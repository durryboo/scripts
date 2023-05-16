#!/usr/bin/python3
# -*- coding: utf-8 -*-
import libtmux
import pwd
from os import system, getlogin, setuid
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from sys import exit

def tmux(command):
    system(f'tmux {command}')

def check_testbox(output, sessionName):
    # Checks if Python is already running or if users are logged into the testbox and will stop and kill the session if there is.
    if 'PYTHON:' in output:
        print('Python scripts already running on testbox, stopping run')
        tmux(f'kill-session -t "{sessionName}"')
        exit()
    if 'USERS:' in output:
        print('Other users are logged into testbox, stopping run')
        tmux(f'kill-session -t "{sessionName}"')
        exit()
    else:
        return

def main():
    user = getlogin()
    uid = pwd.getpwnam(user)[2]
    setuid(uid)

    testSuiteFolder = {
        '1330': '1330_vcs_failover',       '1331': '1331_past_issues',          '1332': '1332_lldp_med',        '1333': '1333_dhcp_snoop',  
        '1334': '1334_epsr',               '1335': '1335_pbr',                  '1336': '1336_acl',             '1337': '1337_cli_walk',           
        '1338': '1338_cont_reboot',        '1339': '1339_atmf',                 '1340': '1340_past_issues_2',   '1341': '1341_limits', 
        '1342': '1342_system_performance', '1343': '1343_vcs_stability',        '1344': '1344_qos',             '1345': '1345_filesystem', 
        '1346': '1346_swi_misc',           '1347': '1347_route_redistribution', '1348': '1348_security',        '1350': '1350_table_entries',
        '1351': '1351_gratuitous_arp',     '1352': '1352_vcs_lag',              '1353': '1353_router',          '1354': '1354_oftest', 
        '1355': '1355_nlb',                '1356': '1356_api',                  '1357': '1357_swi_misc_2',      '1358': '1358_poe_basic', 
        '1359': '1359_modbus',             '1360': '1360_bfd',                  '1361': '1361_mac_learning',    '1362': '1362_multicast', 
        '1363': '1363_ipv6',               '1364': '1364_vrf_limits',           '1365': '1365_mrp',             '1366': '1366_vrf_lite', 
        '1367': '1367_security_failover',  '1368': '1368_layer_3_jumbo_frames', '1399': '1399_system_recovery', '6000': '6000_link_check',    
        '6001': '6001_ART_runup',          '6002': '6002_LUS',                  '6003': '6003_AMF_Release_Interop', 
        '6006': '6006_Router_Performance', '6008': '6008_ART_runup_ext',        '6009': '6009_ART_factory_test',
        '6010': '6010_ART_interface_test', '6100': '6100_system_maintenance',   '6400': '6400_lup_environment',}

    # Parse arguments
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'test',
        help='Sets a test to run. input: Suite.Set.Case')
    parser.add_argument(
        'testbox',
        help='Sets a testbox to use e.g. input: X = tbX')
    parser.add_argument(
        'pylib_folder',
        help='Specify name of pylib folder to use in tb home')
    parser.add_argument(
        '-b', '--build',
        default='main-latest',
        help='Sets a build name to use')
    parser.add_argument(
        '-N', '--noconfig',
        action='store_true',
        help='RTMT with -N option')
    parser.add_argument(
        '-P', '--power',
        action='store_true',
        help='Power off devices after a pass result')
    parser.add_argument(
        '-r1', '--runonce',
        action='store_true',
        help='Runs the test once instead of RTMT')
    parser.add_argument(
        '-F', '--force',
        action='store_true',
        help='Kills other python scripts and users on testbox to run the test')
    parser.add_argument(
        '-u', '--unsupported',
        action='store_true',
        help='Runs the test with --unsupported')
    parser.add_argument(
        '-c', '--config',
        default='',
        help='Sets a config file to use')
    parser.add_argument(
        '-s', '--setup',
        default='',
        help='Sets a setup file to use')
    parser.add_argument(
        '-f', '--failure',
        default='',
        help='Sets failure text to check for')
    parser.add_argument(
        '-lf', '--logfails',
        action='store_true',
        help='Logs failures within the default tmux session named 0')
    knownargs, unknownargs = parser.parse_known_args()
    if len(unknownargs) > 0:
        print(f'Unknown arguments: {unknownargs}')
        exit()
    args = vars(knownargs)

    # Set parameters
    testAttribute = args['test'].split('.')
    testSuite = testAttribute[0]
    testSet = testAttribute[1]
    testCase = testAttribute[2]

    testBox, pylib_folder, build = args['testbox'], args['pylib_folder'], args['build']
    failure, runOnce, force, logFails = args['failure'], args['runonce'], args['force'], args['logfails']

    configFile = ('-c ' + args['config']) if args['config'] else ''
    setupFile = ('-s ' + args['setup']) if args['setup'] else ''
    unsupported = '-u' if args['unsupported'] else ''
    noConfig = '-N' if args['noconfig'] else ''
    Power = '-P' if args['power'] else ''

    startDirectory = f'main_pylib/{pylib_folder}/testsuites_art/{testSuiteFolder[testSuite]}'
    sessionName = f'{testSuite} {testSet} {testCase} tb{testBox} {pylib_folder}'

    logTest = 'clear ; tail -n 10000 -F current_test_log'
    logResult = f'clear ; tail -n 10000 -F current_test_log | egrep -a "FAIL: {failure}|Test case ({testCase}) has been marked as unsupported|\.tgz|^<<|^>>"'
    logSwi = 'clear ; tail -n 10000 -F swi_a.log'

    panes = []
    # Sets the TMUX server, session and panes up
    # Start server and session detached
    tmux('start-server')
    tmux(f'new -d -s "{sessionName}"')
    server = libtmux.Server()
    session = server.find_where({'session_name': sessionName})

    # Set and rename window, split into panes
    window = session.attached_window
    window.rename_window(f'Test {testSuite}.{testSet}.{testCase} on tb{testBox} in folder: {pylib_folder}')
    window.cmd('split-window', '-h')
    window.cmd('split-window', '-f')
    window.cmd('split-window', '-h')
    panes.extend(window.list_panes())

    # Set up test environment
    for i in range(len(panes)):
        panes[i].send_keys(f'ssh tb{testBox}')
        if panes[i] is panes[0]:
            # panes[0].set_height(height=200)
            output = panes[0].capture_pane()
            while f'{user}@tb{testBox}:~$' not in output:
                if force == False:
                    check_testbox(output, sessionName)
                output = panes[0].capture_pane()
        if panes[i] is panes[3]:
            window.select_layout(layout='main-vertical')
            panes[3].resize_pane(width=100)
        panes[i].send_keys(f'cd {startDirectory}')
    window.select_pane('0')

    # Get build
    panes[0].send_keys(f'gb {build}')

    # Run the test
    if testCase.isdigit() and int(testCase) == 0:
        panes[0].send_keys(f'sudo ./test-{testSuite}.{testSet}.py')
    elif runOnce:
        panes[0].send_keys(
            f'sudo ./test-{testSuite}.{testSet}.py {testCase}')
    elif failure != '':
        panes[0].send_keys(
            f'sudo ./rtmt.py {noConfig} {Power} --cf "{failure}|5" ./test-{testSuite}.{testSet}.py {testCase} {configFile} {setupFile} {unsupported}')
    else:
        panes[0].send_keys(
            f'sudo ./rtmt.py {noConfig} {Power} ./test-{testSuite}.{testSet}.py {testCase} {configFile} {setupFile} {unsupported}')

    # Log appropriate files
    panes[2].send_keys(logTest)
    panes[1].send_keys(logResult)
    panes[3].send_keys(logSwi)

    if logFails:
        logSession = server.find_where({'session_name': '0'})
        logWindow = logSession.attached_window
        logPane = logWindow.split_window()
        logPane.select_pane()
        logPane.send_keys(f'cd {startDirectory}')
        logPane.send_keys(logResult)
        logWindow.select_layout(layout='tiled')

    system('tmux a')

main()
