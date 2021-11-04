"""
calphy: a Python library and command line interface for automated free
energy calculations.

Copyright 2021  (c) Sarath Menon^1, Yury Lysogorskiy^1, Ralf Drautz^1
^1: Ruhr-University Bochum, Bochum, Germany

More information about the program can be found in:
Menon, Sarath, Yury Lysogorskiy, Jutta Rogal, and Ralf Drautz. 
“Automated Free Energy Calculation from Atomistic Simulations.” 
ArXiv:2107.08980 [Cond-Mat], July 19, 2021. 
http://arxiv.org/abs/2107.08980.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See the LICENSE file.

For more information contact:
sarath.menon@ruhr-uni-bochum.de
"""

import os
import yaml
import warnings

def check_and_convert_to_list(data):
    """
    Check if the given item is a list, if not convert to a single item list

    Parameters
    ----------
    data : single value or list

    Returns
    -------
    data : list
    """
    if not isinstance(data, list):
        return [data]
    else:
        return data


def prepare_optional_keys(calc, cdict):

    #optional keys
    if "repeat" in calc.keys():
        cdict["repeat"] = calc["repeat"]
        if not (cdict["repeat"][0] == cdict["repeat"][1] == cdict["repeat"][2]):
            raise ValueError("For LAMMPS structure creation, use nx=ny=nz")
    else:
        cdict["repeat"] = [1, 1, 1]
    if "nsims" in calc.keys():
        cdict["nsims"] = calc["nsims"]
    else:
        cdict["nsims"] = 1
    if "thigh" in calc.keys():
        cdict["thigh"] = calc["thigh"]
    else:
        cdict["thigh"] = 2.0*cdict["temperature_stop"]
    if "npt" in calc.keys():
        cdict["npt"] = calc["npt"]
    else:
        cdict["npt"] = True
    if "tguess" in calc.keys():
        cdict["tguess"] = calc["tguess"]
    else:
        cdict["tguess"] = None
    if "dtemp" in calc.keys():
        cdict["dtemp"] = calc["dtemp"]
    else:
        cdict["dtemp"] = 200
    if "maxattempts" in calc.keys():
        cdict["maxattempts"] = calc["maxattempts"]
    else:
        cdict["maxattempts"] = 5

    return cdict

def read_yamlfile(file):
    """
    Read a yaml input file
    Parameters
    ----------
    inputfile: string
        name of inout yaml file
    Returns
    -------
    dict: dict
        the read input dict options
    """
    #there are three blocks - main, md and queue
    #main block has subblocks of calculations

    #we need to set up def options
    options = {}
    
    #main dictionary
    options["element"]: None
    options["mass"]: 1.00

    #create a list for calculations
    options["calculations"] = []

    #options for md
    options["md"] = {
        #pair elements
        "pair_style": None,
        "pair_coeff": None,
        #time related properties
        "timestep": 0.001,
        "nsmall": 10000,
        "nevery": 10,
        "nrepeat": 10,
        "ncycles": 100,
        #ensemble properties
        "tdamp": 0.1,
        "pdamp": 0.1,
        #eqbr and switching time
        "te": 25000,
        "ts": 50000,
        "tguess": None,
        "dtemp": 200,
        "maxattempts": 5,
    }

    #queue properties
    options["queue"] = {
        "scheduler": "local",
        "cores": 1,
        "jobname": "ti",
        "walltime": "23:50:00",
        "queuename": None,
        "memory": "3GB",
        "commands": None,
        "modules": None,
        "options": None
    }

    #convergence factors that can be set if required
    options["conv"] = {
        "alat_tol": 0.0002,
        "k_tol": 0.01,
        "solid_frac": 0.7,
        "liquid_frac": 0.05,
        "p_tol": 0.5,
    }

    #keys that need to be read in directly
    directkeys = ["md", "queue", "conv"]

    #now read the file
    if os.path.exists(file):
        with open(file) as file:
            indata = yaml.load(file, Loader=yaml.FullLoader)
    else:
        raise FileNotFoundError('%s input file not found'% file)


    #now read keys
    for okey in directkeys:
        if okey in indata.keys():
            for key, val in indata[okey].items():
                options[okey][key] = indata[okey][key] 

    options["element"] = check_and_convert_to_list(indata["element"])
    options["mass"] = check_and_convert_to_list(indata["mass"])
    options["md"]["pair_style"] = check_and_convert_to_list(indata["md"]["pair_style"])
    options["md"]["pair_coeff"] = check_and_convert_to_list(indata["md"]["pair_coeff"])

    if not len(options["element"]) == len(options["mass"]):
        raise ValueError("length of elements and mass should be same!")
    options["nelements"] = len(options["element"])

    #now we need to process calculation keys
    #loop over calculations
    if "calculations" in indata.keys():
        #if the key is present
        #Loop 0: over each calc block
        #Loop 1: over lattice
        #Loop 2: over pressure
        #Loop 3: over temperature if needed - depends on mode
        for calc in indata["calculations"]:
            #check and convert items to lists if needed
            mode = calc["mode"]
            
            #now start looping
            #First handle the complex protocols, otherwise go to other simple protocols
            if (mode=='melting_temperature'):
                cdict = {}
                cdict["mode"] = calc["mode"]
                #only read temp if provided
                #if len(temperature)==2:
                #    cdict["temperature"] = temperature[0]
                #    cdict["temperature_stop"] = temperature[-1]
                #else:
                cdict["temperature"] = 0
                cdict["temperature_stop"] = 0

                #pressure is zero
                cdict["pressure"] = 0
                cdict["lattice"] = None
                cdict["state"] = None
                cdict["nelements"] = options["nelements"]
                cdict["element"] = options["element"]
                cdict["lattice_constant"] = 0
                cdict["iso"] = False
                cdict["fix_lattice"] = False
                cdict = prepare_optional_keys(calc, cdict)
                options["calculations"].append(cdict)                      


            #now handle other normal modes
            else:   
                lattice = check_and_convert_to_list(calc["lattice"])
                state = check_and_convert_to_list(calc["state"])
                pressure = check_and_convert_to_list(calc["pressure"])
                temperature = check_and_convert_to_list(calc["temperature"])

                #prepare lattice constant values
                if "lattice_constant" in calc.keys():
                    lattice_constant = check_and_convert_to_list(calc["lattice_constant"])
                else:
                    lattice_constant = [0 for x in range(len(lattice))]
                #prepare lattice constant values
                if "iso" in calc.keys():
                    iso = check_and_convert_to_list(calc["iso"])
                else:
                    iso = [True for x in range(len(lattice))]

                if "fix_lattice" in calc.keys():
                    fix_lattice = check_and_convert_to_list(calc["fix_lattice"])
                else:
                    fix_lattice = [False for x in range(len(lattice))]


                for i, lat in enumerate(lattice):
                    for press in pressure:
                        if (mode == "ts") or (mode == "mts"):
                            cdict = {}
                            cdict["mode"] = calc["mode"]
                            #we need to check for temperature length here
                            if not len(temperature)==2:
                                raise ValueError("At least two temperature values are needed for ts")
                            cdict["temperature"] = temperature[0]
                            cdict["pressure"] = press
                            cdict["lattice"] = lat
                            if state[i] in ['solid', 'liquid']:
                                cdict["state"] = state[i]
                            else:
                                raise ValueError('state has to be either solid or liquid')
                            cdict["temperature_stop"] = temperature[-1]
                            cdict["nelements"] = options["nelements"]
                            cdict["element"] = options["element"]
                            cdict["lattice_constant"] = lattice_constant[i]
                            cdict["iso"] = iso[i]
                            cdict["fix_lattice"] = fix_lattice[i]
                            cdict = prepare_optional_keys(calc, cdict)
                            options["calculations"].append(cdict)                      
                        else:
                            for temp in temperature:
                                cdict = {}
                                cdict["mode"] = calc["mode"]
                                cdict["temperature"] = temp
                                cdict["pressure"] = press
                                cdict["lattice"] = lat
                                if state[i] in ['solid', 'liquid']:
                                    cdict["state"] = state[i]
                                else:
                                    raise ValueError('state has to be either solid or liquid')

                                cdict["temperature_stop"] = temp
                                cdict["nelements"] = options["nelements"]
                                cdict["element"] = options["element"]
                                cdict["lattice_constant"] = lattice_constant[i]
                                cdict["iso"] = iso[i]
                                cdict["fix_lattice"] = fix_lattice[i]
                                cdict = prepare_optional_keys(calc, cdict)
                                options["calculations"].append(cdict)

                                if mode == "alchemy":
                                    #if alchemy mode is selected: make sure that hybrid pair styles
                                    if not len(options["md"]["pair_style"]) == 2:
                                        raise ValueError("Two pair styles need to be provided")
    return options

def create_identifier(calc):
    """
    Generate an identifier

    Parameters
    ----------
    calc: dict
        a calculation dict

    Returns
    -------
    identistring: string
        unique identification string
    """
    #lattice processed
    prefix = calc["mode"]

    if prefix == 'melting_temperature':
        ts = int(0)
        ps = int(0)

        l = 'tm'

    else:
        ts = int(calc["temperature"])
        ps = int(calc["pressure"])

        l = calc["lattice"]
        l = l.split('/')
        l = l[-1]


    identistring = "-".join([prefix, l, str(ts), str(ps)])
    return identistring

def read_inputfile(file):
    """
    Read calphy inputfile

    Parameters
    ----------
    file : string
        input file

    Returns
    -------
    options : dict
        dictionary containing input options

    """
    options = read_yamlfile(file)

    for i in range(len(options["calculations"])):
        identistring = create_identifier(options["calculations"][i])
        options["calculations"][i]["directory"] = identistring

    return options