import collections
import re
import sys
import os
import argparse
from os import listdir
from os.path import isfile, join
import subprocess
import time

## DWI pre-processing script for Man

# mrconvert -fslgrad 003.bvec 003.bval 003-dwi.nii.gz 003-dwi.mif
# dwidenoise 003-dwi.mif 003-dwi-denoised.mif -noise 003-noise.mif
# dwipreproc  AP 003-dwi-denoised.mif -rpe_pair AP003.nii.gz PA003.nii.gz 003-dwi-processed.mif
# dwibiascorrect 003-dwi-processed.mif 003-dwi-biascorrected.mif -fsl
# dwi2mask 003-dwi-biascorrected.mif 003-dwi-mask.mif
# dwi2response tournier 003-dwi-biascorrected.mif 003-response.txt
# dwi2fod csd 003-dwi-biascorrected.mif 003-response.txt 003-fod.mif -mask 003-dwi-mask.mif



def get_filenameprefix(filename):
    """
    Extract prefix from input filename
    :param filename:
    :return: prefix (digits 1-6)
    """
    pattern = '^(\d{1,6})(.*).nii.gz'
    #p = re.compile(pattern)
    return re.search(pattern, filename, re.S).group(1)

def file_check(fn):
    """
    Check that file exists and is readable
    :param fn:
    :return:
    """
    try:

        open(fn, "r")
        return 1
    except IOError:
        print("Error: File not found or cannot be accessed:", fn)
        return 0
    except PermissionError:
        print("Error: File maybe open in another program or does not exist:", fn)
        return 0

def create_programlist(filename_prefix):
    """
    Creates a programlist with the filename_prefix
    Requires dictionary of program commandlines with:
        program: name of program
        options: usually with hyphens eg -fsl
        inputfiles: list of files to be used in input - parsed with filename_prefix
            eg %s is the placeholder for the prefix
        outputfile: name of outputfile

    :param filename_prefix:
    :return:
    """
    programlist=[]

    programs = collections.OrderedDict([('1',{'program':'mrconvert', 'options': '-fslgrad',
                                              'inputfiles':['%s.bvec', '%s.bval', '%s-dwi.nii.gz'],
                                              'outputfile': '%s-dwi.mif' }),
                                        ('2',{'program':'dwidenoise','options':'-noise',
                                              'inputfiles': ['%s-dwi.mif', '%s-dwi-denoised.mif'],
                                              'outputfile':'%s-noise.mif'}),
                                        ('3',{'program': 'dwipreproc','pre':'AP %s-dwi-denoised.mif','options': '-rpe_pair',
                                              'inputfiles': ['AP%s.nii.gz', 'PA%s.nii.gz'],
                                              'outputfile':'%s-dwi-processed.mif'}),
                                        ('4',{'program':'dwibiascorrect', 'options':'-fsl',
                                              'inputfiles':['%s-dwi-processed.mif'],
                                              'outputfile': '%s-dwi-biascorrected.mif'}),
                                        ('5',{'program':'dwi2mask', 'options':'',
                                              'inputfiles':['%s-dwi-biascorrected.mif'],
                                              'outputfile':'%s-dwi-mask.mif'}),
                                        ('6', {'program': 'dwi2response', 'options': 'tournier',
                                               'inputfiles': ['%s-dwi-biascorrected.mif'],
                                               'outputfile': '%s-response.txt'}),
                                        ('7', {'program': 'dwi2fod', 'options': '-mask',
                                               'inputfiles': ['%s-dwi-biascorrected.mif', '%s-response.txt','%s-fod.mif' ],
                                               'outputfile': '%s-dwi-mask.mif'}),
                                        ])

    if filename_prefix:
        for i,v in programs.items():
            #print(i, "=", v['program'])
            inputfiles = ''
            for input in  v['inputfiles']:
                inputfiles += input % filename_prefix
                inputfiles += " "

            outputfile = v['outputfile'] % filename_prefix
            if 'pre' in v:
                pre = v['pre'] % filename_prefix
                process_string = '%s %s %s %s %s' % (v['program'], pre, v['options'], inputfiles, outputfile)
            else:
                process_string = '%s %s %s %s' % (v['program'], v['options'], inputfiles, outputfile)
            programlist.append(process_string)
    else:
        print('Unable to get filename prefix - stopping')
    return programlist

def processinputfile(inputfile, checkflag=False):
    """
    Set up and run file processing
    :param filename:
    :return: status
    """
    if checkvalidinput(inputfile) and os.path.exists(inputfile):
        filename = os.path.basename(inputfile)
        filename_prefix = get_filenameprefix(filename)
        if filename_prefix:
            #print("Prefix is: ", filename_prefix)
            programlist = create_programlist(filename_prefix)
            if checkflag:
                print("\n******Checking programlist (no run) for ", inputfile, "*********\n")
            else:
                print("\n******Running programlist for ", inputfile, "*********\n")
            num= 0
            for program in programlist:
                num +=1
                if checkflag:
                    print(program)
                else:
                    print("Executing program: ", num, ":", program)
                    parts = program.split(" ")
                    #Test with ping: p = subprocess.Popen(["ping", "-n","2","www.bigpond.com"], stdout=subprocess.PIPE)
                    p = subprocess.Popen(parts, stdout=subprocess.PIPE)
                    output, err = p.communicate()
                    print(output)


        else:
            print("ERROR: Unable to extract filename_prefix - cannot continue")
            sys.exit(0)

def checkvalidinput(checkname):
    if re.search('[a-zA-Z0-9\-\\\/\.\_]+', checkname):
        return True
    else:
        return False

def main():
    """
    Main program control
    1. Reads directory in from commandline or assumes current directory
    2. For each file
        a. extracts filename_prefix
        b. creates programlist with filename_prefix
    3. Runs through each program in the list - waits for completion
    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dirname", dest="inputdir",action="store",
                        help="Full path to input directory")
    parser.add_argument("-f", "--filename", dest="inputfile",action="store",
                        help="Full path to input file")
    parser.add_argument("-c", "--check", dest="checkconfig",action="store_true",
                        help="Check commands without running")

    args = parser.parse_args()
    #Just output commands without running
    if args.checkconfig:
        checkflag= True
    else:
        checkflag = False

    if args.inputdir:
        #Check directory is valid
        if checkvalidinput(args.inputdir) and os.path.exists(args.inputdir) and os.stat(args.inputdir).st_size > 0:
            #loop through a directory of nii.gz files
            print("Loop through directory: ", args.inputdir)
            gzfiles = [f for f in listdir(args.inputdir) if isfile(join(args.inputdir, f)) and os.path.splitext(f)[1]=='.gz']
            for inputfile in gzfiles:
                processinputfile(join(args.inputdir,inputfile), checkflag)

        else:
            print("Directory is not valid or does not contain any files - exiting")
            sys.exit(0)
    elif args.inputfile:
        processinputfile(args.inputfile, checkflag)

    else:
        print('ERROR: No files specified')
        sys.exit(0)


if __name__ == '__main__':
    main()