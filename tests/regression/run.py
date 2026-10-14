#!/usr/bin/env python3
"""Build fresh baseline/candidate checkouts and run the same end-to-end cases."""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import time

import numpy as np
from configobj import ConfigObj
from compare import close, force, lightcone, numeric, particles, TOLERANCES

HERE = Path(__file__).resolve().parent
BASELINE = 'd8cd89b2a8118f99c7b71c4e7cf6963860073612'
CASES = ('gr', 'horndeski', 'kmouflage', 'lightcone')
LOG = logging.getLogger(__name__)


def command(argv, cwd, log, timeout=900):
    """Keep commands and output after failures; kill MPI children on timeout."""
    argv = [str(x) for x in argv]
    log.parent.mkdir(parents=True,exist_ok=True)
    start = time.monotonic()
    with log.open('w') as stream:
        with subprocess.Popen(argv,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,
                              start_new_session=True) as process:
            info = dict(command=argv,cwd=str(cwd),host=socket.gethostname(),pid=process.pid,
                        log=str(log),stop=f'kill -TERM -- -{process.pid}')
            print(json.dumps(info),flush=True)
            log.with_suffix('.command.json').write_text(json.dumps(info,indent=2)+'\n')
            try:
                code = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired,KeyboardInterrupt):
                os.killpg(process.pid,signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL)
                    process.wait()
                raise
    info.update(returncode=code,elapsed_seconds=time.monotonic()-start)
    log.with_suffix('.command.json').write_text(json.dumps(info,indent=2)+'\n')
    if code:
        raise RuntimeError(f'Exit {code}: {shlex.join(argv)}; see {log}')


def git(repo, *args):
    return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()


def clone(repo, ref, dest):
    # Clone through Git rather than copying the developer's working files or objects.
    command(['git','clone','--no-local','--no-checkout',repo,dest],dest.parent,dest.parent/'clone.log')
    try:
        resolved = git(dest,'rev-parse','--verify','--quiet',ref+'^{commit}')
    except subprocess.CalledProcessError:
        resolved = git(dest,'rev-parse','--verify',f'refs/remotes/origin/{ref}^{{commit}}')
    command(['git','checkout','--detach',resolved],dest,dest.parent/'checkout.log')
    command(['git','submodule','update','--init','--recursive'],dest,dest.parent/'dependencies.log')
    return dict(commit=git(dest,'rev-parse','HEAD'),submodules=git(dest,'submodule','status','--recursive'))


def make_args(source, args, baseline=False):
    prefix = args.prefix
    backend = source/('HiCOLA/FML/COLASolver' if baseline else args.backend)
    include = source/('HiCOLA' if baseline else args.fml_include)
    values = ['make','-C',backend,'-j2',f'FML_INCLUDE={include}','USE_MPI=true','USE_OMP=false']
    for library in ('FFTW','GSL','LUA'):
        values += [f'{library}_INCLUDE={prefix}/include',f'{library}_LIB={prefix}/lib']
    values += args.make_arg
    return backend,values


def build(source, args, baseline=False):
    backend,values = make_args(source,args,baseline)
    command(values,source,source.parent/'build.log',timeout=1200)
    # The probe links the application's real compiled numerical objects.
    probe_make = source.parent/'force-probe.mk'
    probe_make.write_text('force_probe: $(filter-out Main.o,$(OBJS))\n'
        f'\t$(CC) $(OPTIONS) $(INC) -Isrc {HERE / "force_probe.cpp"} -o $@ $^ $(LIB) $(LINK)\n')
    command(values+['-f','Makefile','-f',probe_make,'force_probe'],source,source.parent/'probe-build.log',timeout=1200)
    for name in ('nbody','force_probe'):
        if not (backend/name).is_file():
            raise RuntimeError(f'Missing build output: {backend/name}')
    return backend


def frontend(source, work, model):
    out = work/'frontend'/model
    out.mkdir(parents=True)
    if model == 'kmouflage':
        # Manufactured nonzero coupling/screening inputs isolate the backend migration.
        a = np.geomspace(1e-4,1.,200)
        r, m = 4.28e-5/.7307**2, (.02196+.1274)/.7307**2
        E2 = r/a**4+m/a**3+1-r-m
        expansion = np.column_stack((a,np.sqrt(E2),-.5*(4*r/a**4+3*m/a**3)/E2))
        data = {'expansion':expansion,'force':np.column_stack((a,np.full_like(a,1e4),np.full_like(a,.02)))}
        paths = {}
        for name,values in data.items():
            paths[name] = out/f'{model}_regression_{name}.txt'
            np.savetxt(paths[name],values)
        return paths
    theory = ConfigObj(str(HERE/f'{model}.ini'))
    theory['output_directory'] = str(out)
    theory['model_name'] = model
    theory.filename = str(out/'model.ini')
    theory.write()
    config = ConfigObj(str(HERE/'numerical.ini'))
    config.update(dict(Npoints='400',max_redshift='9999',suppression_flag='False',forwards_flag='False'))
    config.filename = str(out/'numerical.ini')
    config.write()
    module = 'generate_simulation_input'
    command([sys.executable,'-m',f'HiCOLA.Frontend.{module}',theory.filename,config.filename],source,out/'run.log')
    paths = {}
    for name in ('expansion','force','full'):
        matches = list(out.glob(f'{model}_*_{name}.txt'))
        if len(matches) != 1:
            raise RuntimeError(f'Expected one {model} {name} table; got {matches}')
        data = numeric(matches[0])
        if len(data) != 400 or not (np.all(np.diff(data[:,0])>0) or np.all(np.diff(data[:,0])<0)):
            raise ValueError(f'Invalid frontend scale-factor grid: {matches[0]}')
        paths[name] = matches[0]
    return paths


def lua(source, folder, case, tables):
    """Generate a complete small configuration from the frozen shipped template."""
    text = (HERE/'backend.lua').read_text()
    # Append overrides after loading the template so conditionals cannot reset them.
    values = dict(all_parameters_must_be_in_file=False,simulation_name=case,
        simulation_boxsize=256., particle_Npart_1D=16, particle_allocation_factor=4.,
        ic_nmesh=16, force_nmesh=32, pofk_nmesh=32, output_particles=True,
        output_folder=str(folder/'output'),output_fileformat='GADGET',
        ic_random_seed=1234,ic_fix_amplitude=True,ic_initial_redshift=49.,
        force_linear_massive_neutrinos=False,cosmology_model='LCDM',gravity_model='GR',
        cosmology_h=.7307,cosmology_Omegab=.02196/.7307**2,
        cosmology_OmegaCDM=.1274/.7307**2,cosmology_OmegaMNu=0.,
        ic_input_filename=str(source/'HiCOLA/Parameter_files/Backend_parameter_files/LCDM_1306dot3219_matterpower_z0.000.dat'),
        lightcone=case=='lightcone',plc_pos_observer=[.5,.5,.5],
        plc_z_init=.05,plc_z_finish=0.,plc_use_replicas=False,plc_boundary_mpch=0.,
        plc_output_asciifile=True,plc_output_gadgetfile=False,plc_output_in_batches=False,
        plc_make_onion_density_maps=False,fof=False,pofk=True,
        output_redshifts=[0.],timestep_nsteps=[5])
    if case in ('horndeski','kmouflage'):
        values.update(cosmology_model='HiCOLA',gravity_model='HiCOLA' if case=='horndeski' else 'kmouflage',
            HiCOLA_expansion_filename=str(tables['expansion']),HiCOLA_preforce_filename=str(tables['force']),
            gravity_model_screening=True,gravity_model_HiCOLA_smoothing_filter='gaussian',
            gravity_model_HiCOLA_smoothing_scale_over_boxsize=3./256.,
            gravity_model_screening_enforce_largescale_linear=True,gravity_model_screening_linear_scale_hmpc=.1)
    def literal(value):
        if isinstance(value,bool):
            return str(value).lower()
        if isinstance(value,list):
            return '{'+','.join(map(literal,value))+'}'
        return json.dumps(value)
    text += '\n-- Deterministic regression run overrides.\n'
    text += '\n'.join(f'{key} = {literal(value)}' for key,value in values.items())+'\n'
    path = folder/'run.lua'
    path.write_text(text)
    return path


def run_cases(source, backend, work, args):
    tables = {model:frontend(source,work,model) for model in ('horndeski','kmouflage')}
    for ranks in args.ranks:
        for case in args.cases:
            folder = work/f'{case}-np{ranks}'
            folder.mkdir()
            config = lua(source,folder,case,tables.get(case))
            launch = ['mpiexec','-n',ranks]
            command(launch+[backend/'nbody',config],source,folder/'run.log')
            log = (folder/'run.log').read_text()
            if 'Doing output 0 at redshift z = 0' not in log:
                raise ValueError(f'{case}: did not output the final epoch')
            for screened in (False,True) if case in ('horndeski','kmouflage') else (False,):
                probe_config = folder/f'force-{screened}.lua'
                text = config.read_text()+f'\ngravity_model_screening = {str(screened).lower()}\n'
                # Stress the gradient screening with a manufactured, finite coefficient.
                if screened and case=='kmouflage':
                    table = numeric(tables[case]['force']).copy()
                    table[:,1] = 1e4
                    path = folder/'screening-stress.txt'
                    np.savetxt(path,table)
                    text += f'HiCOLA_preforce_filename = {json.dumps(str(path))}\n'
                probe_config.write_text(text)
                command(launch+[backend/'force_probe',probe_config,folder/f'force-{screened}'],source,folder/f'force-{screened}.log')


def compare_runs(baseline, candidate, args):
    results = {}
    for model in ('horndeski','kmouflage'):
        for name in (('expansion','force','full') if model=='horndeski' else ('expansion','force')):
            ref = next((baseline/'frontend'/model).glob(f'{model}_*_{name}.txt'))
            got = candidate/'frontend'/model/ref.name
            results[f'{model}/frontend/{name}'] = close(numeric(got),numeric(ref),'tables')
    for ranks in args.ranks:
        for case in args.cases:
            key = f'{case}-np{ranks}'
            ref,got = baseline/key/'output',candidate/key/'output'
            reference_files = sorted(p.relative_to(ref) for p in ref.rglob('*.txt') if not p.relative_to(ref).parts[0].startswith('lightcone_'))
            actual_files = sorted(p.relative_to(got) for p in got.rglob('*.txt') if not p.relative_to(got).parts[0].startswith('lightcone_'))
            if actual_files != reference_files or not reference_files:
                raise ValueError(f'{key}: output file inventory differs or is empty')
            if not list(ref.glob('gravitymodel_*')) or not list(ref.rglob('pofk*txt')):
                raise ValueError(f'{key}: missing growth or power spectrum')
            for path in reference_files:
                kind = 'power' if 'pofk' in path.name else 'tables'
                results[f'{key}/{path}'] = close(numeric(got/path),numeric(ref/path),kind)
            ref_parts = sorted(ref.rglob('gadget_z0.000.*'))
            got_parts = sorted(got.rglob('gadget_z0.000.*'))
            if len(ref_parts)!=ranks or len(got_parts)!=ranks:
                raise ValueError(f'{key}: missing snapshot rank files')
            ids,p,v = particles(ref_parts)
            got_ids,got_p,got_v = particles(got_parts)
            np.testing.assert_array_equal(got_ids,ids)
            results[f'{key}/positions'] = close(got_p,p,'positions')
            results[f'{key}/velocities'] = close(got_v,v,'velocities')
            for screened in (False,True) if case in ('horndeski','kmouflage') else (False,):
                a = sorted((baseline/key).glob(f'force-{screened}.*.txt'))
                b = sorted((candidate/key).glob(f'force-{screened}.*.txt'))
                if len(a)!=ranks or len(b)!=ranks:
                    raise ValueError(f'{key}: missing force rank files')
                a,b = force(a),force(b)
                np.testing.assert_array_equal(a[:,:3],b[:,:3])
                results[f'{key}/force-{screened}'] = close(b[:,3:],a[:,3:],'force')
            if case=='lightcone':
                results[f'{key}/lightcone'] = close(lightcone(sorted(got.rglob('*ascii_step*'))),
                    lightcone(sorted(ref.rglob('*ascii_step*'))),'lightcone')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',default=str(Path.cwd()))
    parser.add_argument('--candidate-ref',default='HEAD')
    parser.add_argument('--work',type=Path,required=True,help='New directory for checkouts, logs and artifacts')
    parser.add_argument('--prefix',type=Path,default=os.environ.get('CONDA_PREFIX'))
    parser.add_argument('--backend',default='HiCOLA/FML/COLASolver',help='Candidate backend directory relative to checkout')
    parser.add_argument('--fml-include',default='HiCOLA',help='Candidate directory containing FML')
    parser.add_argument('--make-arg',action='append',default=[])
    parser.add_argument('--ranks',type=int,nargs='+',default=[1,2],choices=(1,2))
    parser.add_argument('--cases',nargs='+',choices=CASES,default=list(CASES))
    args = parser.parse_args()
    if args.prefix is None:
        parser.error('Activate the regression conda environment or supply --prefix')
    args.work = args.work.resolve()
    args.work.mkdir(parents=True,exist_ok=False)
    os.environ.update(OMP_NUM_THREADS='1',MPLBACKEND='Agg')
    os.environ['PATH'] = str(args.prefix/'bin')+os.pathsep+os.environ['PATH']
    os.environ.pop('PYTHONPATH',None)
    manifest = dict(baseline=BASELINE, candidate_ref=args.candidate_ref,
        host=socket.gethostname(),python=sys.version,cases=args.cases,ranks=args.ranks,
        tolerances=TOLERANCES,status='running',
        fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(HERE.iterdir()) if p.suffix in ('.ini','.lua','.cpp')})
    try:
        command([sys.executable,'-m','pip','freeze'],args.work,args.work/'environment.log')
        command(['mpicxx','--version'],args.work,args.work/'compiler.log')
        command(['mpiexec','--version'],args.work,args.work/'mpi.log')
        for label,ref in (('baseline',BASELINE),('candidate',args.candidate_ref)):
            work = args.work/label
            work.mkdir()
            source = work/'source'
            manifest[label] = clone(args.repository,ref,source)
            backend = build(source,args,baseline=label=='baseline')
            run_cases(source,backend,work,args)
        manifest['comparisons'] = compare_runs(args.work/'baseline',args.work/'candidate',args)
        manifest['status'] = 'passed'
    except Exception as error:
        manifest.update(status='failed',error=str(error))
        raise
    finally:
        (args.work/'report.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'PASS: {len(manifest["comparisons"])} comparisons; report {args.work/"report.json"}')


if __name__=='__main__':
    main()
