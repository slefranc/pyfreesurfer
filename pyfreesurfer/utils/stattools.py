##########################################################################
# NSAp - Copyright (C) CEA, 2013 - 2016
# Distributed under the terms of the CeCILL-B license, as published by
# the CEA-CNRS-INRIA. Refer to the LICENSE file or to
# http://www.cecill.info/licences/Licence_CeCILL-B_V1-en.html
# for details.
##########################################################################

# Sytem import
import os
import csv
import glob
import numpy

# Pyfreesurfer import
from pyfreesurfer import DEFAULT_FREESURFER_PATH
from pyfreesurfer.wrapper import FSWrapper
from pyfreesurfer.conversions.surftools import mri_surf2surf


def population_summary(fsdir, sid=None):
    """ Compute the mean, std from the FreeSurfer individual scores.
    If a subject identifier is given, return the FreeSurfer subject scores.

    Parameters
    ----------
    fsdir: str (mandatory)
        the FreeSurfer segmentation home directory.
    sid: str (optional, default None)
        if None, compute the statistic from all the FreeSurfer segmentation
        home directory subjects, otherwise return only the specified subject
        scores.

    Returns
    -------
    popstats: dict
        the population statistic or the individual scores.
    """
    # Go through all statistics
    popstats = {
        "lh": {},
        "rh": {},
        "aseg": {}
    }
    stats = glob.glob(os.path.join(fsdir, "stats", "*.csv"))
    for fpath in stats:
        basename = os.path.basename(fpath).split(".")[0]
        if basename.startswith("aseg"):
            stype, _, sname = basename.split("_")
            hemi = "aseg"
            subject_header = "Measure:volume"
        elif basename.startswith("aparc"):
            stype, _, hemi, sname = basename.split("_")
            subject_header = "{0}.{1}.{2}".format(hemi, stype, sname)
        else:
            continue

        if sname not in popstats[hemi]:
            popstats[hemi][sname] = {}
        with open(fpath, "rb") as openfile:
            reader = csv.DictReader(openfile)
            for line in reader:
                subject = line.pop(subject_header)
                if sid is not None:
                    if subject != sid:
                        continue
                for key, value in line.items():
                    popstats[hemi][sname].setdefault(key, []).append(
                        float(value))
        for region_name, values in popstats[hemi][sname].items():
            mean = numpy.mean(values)
            std = numpy.std(values)
            popstats[hemi][sname][region_name] = {
                "values": values,
                "m": mean,
                "s": std
            }

    return popstats


def aparcstats2table(fsdir, outdir, fsconfig=DEFAULT_FREESURFER_PATH):
    """ Generate text/ascii tables of freesurfer parcellation stats data
    '?h.aparc.stats'.

    This can then be easily imported into a spreadsheet and/or stats program.

    Binding over the FreeSurfer's 'aparcstats2table' command.

    Parameters
    ----------
    fsdir: (mandatory)
        The freesurfer working directory with all the subjects.
    outdir: str (mandatory)
        The statistical destination folder.
    fsconfig: str (optional)
        The freesurfer configuration batch.

    Return
    ------
    statfiles: list of str
        The freesurfer summary stats.
    """
    # Check input parameters
    for path in (fsdir, outdir):
        if not os.path.isdir(path):
            raise ValueError("'{0}' is not a valid directory.".format(path))

    # Parameter that will contain the output stats
    statfiles = []

    # Fist find all the subjects with a stat dir
    statdirs = glob.glob(os.path.join(fsdir, "*", "stats"))
    subjects = [item.lstrip(os.sep).split("/")[-2] for item in statdirs]

    # Save the FreeSurfer current working directory and set the new one
    fscwd = None
    if "SUBJECTS_DIR" in os.environ:
        fscwd = os.environ["SUBJECTS_DIR"]
    os.environ["SUBJECTS_DIR"] = fsdir

    # Create the output stat directory
    fsoutdir = os.path.join(outdir, "stats")
    if not os.path.isdir(fsoutdir):
        os.mkdir(fsoutdir)

    # Call freesurfer
    for hemi in ["lh", "rh"]:
        for meas in ["area", "volume", "thickness", "thicknessstd",
                     "meancurv", "gauscurv", "foldind", "curvind"]:

            statfile = os.path.join(
                fsoutdir, "aparc_stats_{0}_{1}.csv".format(hemi, meas))
            statfiles.append(statfile)
            cmd = ["aparcstats2table", "--subjects"] + subjects + [
                "--hemi", hemi, "--meas", meas, "--tablefile", statfile,
                "--delimiter", "comma", "--parcid-only"]

            recon = FSWrapper(cmd, shfile=fsconfig)
            recon()
            if recon.exitcode != 0:
                raise FreeSurferRuntimeError(
                    recon.cmd[0], " ".join(recon.cmd[1:]), recon.stderr +
                    recon.stdout)

    # Restore the FreeSurfer working directory
    if fscwd is not None:
        os.environ["SUBJECTS_DIR"] = fscwd

    return statfiles


def asegstats2table(fsdir, outdir, fsconfig=DEFAULT_FREESURFER_PATH):
    """ Generate text/ascii tables of freesurfer parcellation stats data
    'aseg.stats'.

    This can then be easily imported into a spreadsheet and/or stats program.

    Binding over the FreeSurfer's 'asegstats2table' command.

    Parameters
    ----------
    fsdir: str (mandatory)
        The freesurfer working directory with all the subjects.
    outdir: str (mandatory)
        The statistical destination folder.
    fsconfig: str (optional)
        The freesurfer configuration batch.
        
    Return
    ------
    statfiles: list of str
        The freesurfer summary stats.
    """
    # Check input parameters
    for path in (fsdir, outdir):
        if not os.path.isdir(path):
            raise ValueError("'{0}' is not a valid directory.".format(path))

    # Parameter that will contain the output stats
    statfiles = []

    # Fist find all the subjects with a stat dir
    statdirs = glob.glob(os.path.join(fsdir, "*", "stats"))
    subjects = [item.lstrip(os.sep).split("/")[-2] for item in statdirs]

    # Save the FreeSurfer current working directory and set the new one
    fscwd = None
    if "SUBJECTS_DIR" in os.environ:
        fscwd = os.environ["SUBJECTS_DIR"]
    os.environ["SUBJECTS_DIR"] = fsdir

    # Create the output stat directory
    fsoutdir = os.path.join(outdir, "stats")
    if not os.path.isdir(fsoutdir):
        os.mkdir(fsoutdir)

    # Call freesurfer
    statfile = os.path.join(fsoutdir, "aseg_stats_volume.csv")
    statfiles.append(statfile)
    cmd = ["asegstats2table", "--subjects"] + subjects + [
        "--meas", "volume", "--tablefile", statfile, "--delimiter", "comma"]
    recon = FSWrapper(cmd, shfile=fsconfig)
    recon()
    if recon.exitcode != 0:
        raise FreeSurferRuntimeError(
            recon.cmd[0], " ".join(recon.cmd[1:]), recon.stderr +
            recon.stdout)

    # Restore the FreeSurfer working directory
    if fscwd is not None:
        os.environ["SUBJECTS_DIR"] = fscwd

    return statfiles


def textures2table(
        regex,
        ico_order,
        fsdir,
        outdir=None,
        keep_individual_textures=False,
        save_mode="numpy",
        fsconfig=DEFAULT_FREESURFER_PATH):
    """ Generate text/ascii tables of freesurfer textures data.

    This can then be easily imported into a spreadsheet and/or stats program.
    Note that all the subject texture vertices need to be resampled in a common
    space.

    Parameters
    ----------
    regex: str (mandatory)
        a regular expression used to locate the files to be converted from
        the 'fsdir' directory.
    ico_order: int (mandatory)
        icosahedron order in [0, 7] that will be used to generate the cortical
        surface texture at a specific tessalation (the corresponding cortical
        surface can be resampled using the
        'clindmri.segmentation.freesurfer.resample_cortical_surface' function).
    fsdir: str (mandatory)
        FreeSurfer subjects directory 'SUBJECTS_DIR'.
    outdir: str (optional, default None)
        a folder where some information about the processing could
        be written.
    keep_individual_textures: bool (optional, default False)
        if True, keep the individual resampled subject textures on disk.
    save_mode: str (optional, default 'numpy')
        save result in 'csv' or in 'numpy' or 'all'. In CSV format we keep
        only 4 digits and in Numpy format we save several single arrays into
        a single file.
    fsconfig: str (optional)
        the FreeSurfer '.sh' config file.

    Returns
    -------
    textures_files: list of str
        a list of file containing the selected subjects summary texture values.
    """
    # Check input parameters
    if save_mode not in ["numpy", "csv", "all"]:
        raise ValueError("'{0}' is not a valid save option must be "
                         "in ['numpy', 'csv', 'all']".format(save_mode))

    # Get the requested subject textures from the regex
    textures = glob.glob(os.path.join(fsdir, regex))
    if outdir is not None:
        path = os.path.join(outdir, "textrues.json")
        with open(path, "w") as open_file:
            json.dump(textures, open_file, indent=4)

    # Resample each texture file
    basename = os.path.basename(regex)
    fsoutdir = os.path.join(fsdir, "textures")
    surfacesdir = os.path.join(fsoutdir, basename)
    if not os.path.isdir(surfacesdir):
        os.makedirs(surfacesdir)
    textures_map = {}
    for texturefile in textures:

        # Get the subject id
        sid = texturefile.replace(fsdir, "")
        sid = sid.lstrip(os.sep).split(os.sep)[0]

        # Get the hemisphere
        hemi = basename.split(".")[0]

        # Create the destination resamples texture file
        resampled_texturefile = os.path.join(surfacesdir, "{0}_{1}.mgz".format(
            sid, basename))

        # Reasmple the surface
        mri_surf2surf(hemi, texturefile, resampled_texturefile,
                      ico_order=ico_order, fsdir=fsdir, sid=sid,
                      fsconfig=fsconfig)

        # Check that the resampled texture has the expected size
        profile_array = nibabel.load(resampled_texturefile).get_data()
        profile_dim = profile_array.ndim
        profile_shape = profile_array.shape
        if profile_dim != 3:
            raise ValueError(
                "Expected profile texture array of dimension 3 not "
                "'{0}'".format(profile_dim))
        if (profile_shape[1] != 1) or (profile_shape[2] != 1):
            raise ValueError(
                "Expected profile texture array of shape (*, 1, 1) not "
                "'{0}'.".format(profile_shape))

        # Organize the resampled textures in a single file
        if sid in textures_map:
            raise ValueError("Subject '{0}' already treated. Check the intput "
                             "'regex'.".format(sid))
        textures_map[sid] = profile_array.ravel().astype(numpy.single)

    # Remove surfaces folder
    if not keep_individual_textures:
        shutil.rmtree(surfacesdir)

    # Save textures in CSV or in Numpy
    textures_files = []
    if save_mode in ["csv", "all"]:
        textures_file = os.path.join(fsoutdir, basename + ".csv")
        with open(textures_file, "wb") as open_file:
            csv_writer = csv.writer(open_file, delimiter=",")
            for sid in sorted(textures_map.keys()):
                row = [sid]
                row.extend(
                    ["{0:.4f}".format(elem) for elem in textures_map[sid]])
                csv_writer.writerow(row)
        textures_files.append(textures_file)
    if save_mode in ["numpy", "all"]:
        textures_file = os.path.join(fsoutdir, basename + ".npz")
        numpy.savez(textures_file, **textures_map)
        textures_files.append(textures_file)

    return textures_files

