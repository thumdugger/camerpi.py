#!/usr/bin/python

import click
import math
import re
import subprocess

from pprint import pp

@click.group("camerpi")
@click.option(
    "--list-cameras", "camerpi_cameras_list"
    , help="Display list of available cameras"
    , type=str, default="", show_default=False)
@click.option(
    "--list-modes-for", "camerpi_modes_list"
    , help="Display list of modes for CAMERA[,CAMERA...] (indexes as from --list-cameras or 'ALL')"
    , type=str, default="", show_default=False)
@click.option(
    "--list-resolutions-for", "camerpi_resolutions_list"
    , help="Display list of resolutions for MODE[,MODE...]  (indexes as from --list-modes or 'ALL')"
    , type=str, default="", show_default=False)
@click.pass_context
def camerpi_grp(ctx, camerpi_cameras_list, camerpi_modes_list, camerpi_resolutions_list):
    """Wrapper for libcamera-* commands"""
    
    completed_process = subprocess.run(
        ["libcamera-still", "--list-cameras"]
        , capture_output=True)
    if 0 != completed_process.returncode:
        raise RuntimeError(
            f"libcamera-still failed with error code:" 
            f"{completed_process.returncode} : "
            f"{completed_process.stderr.decode(encoding='utf-8', errors='strict')}")
    
    cameras = {}
    camera_mode_index = -1
    camera_mode_resolution_index = -1
    
    for row in completed_process.stdout.decode(encoding="utf-8", errors="strict").split("\n"):
        row = row.strip()
        if not re.match(r"Modes:|\d{1,2}\s?:|\d+x\d+", row):
            # ignore empty lines and "decoration" lines
            continue

        if ms := re.match(r"(\d{1,2}) : (\w+) \[(\d+)x(\d+)\] \(([^\)]+)\)$", row):
            # found a new camera device listing
            camera_index = f"C{ms.group(1)}"
            camera = cameras[camera_index] = {
                "camera-index": camera_index
                , "dtoverlay": ms.group(2)
                , "sensor-resolution": (int(ms.group(3)), int(ms.group(4)))
                , "device": ms.group(5)}
            camera_modes = camera["modes"] = {}
            continue
        
        if ms := re.match(r"Modes: '(S([RGB]{4})(\d+)_(\w+))'", row):
            # found start of modes list
            camera_mode_index += 1
            mode_index = f"M{camera_mode_index}"
            camera_mode = camera_modes[mode_index] = {
                "mode-index": mode_index
                , "mode": ms.group(1)
                , "bayer-order": ms.group(2)
                , "bit-depth": int(ms.group(3))
                , "packing": ms.group(4)}
            camera_mode_resolutions = camera_mode["resolutions"] = {}
        
        if ms := re.match(
            r"(\d+)x(\d+) \[(\d+\.\d+) fps - \((\d+), (\d+)\)/(\d+)x(\d+) crop\]$"
            , row
        ):  # found a resolution mode entry
            camera_mode_resolution_index += 1
            resolution_index = f"R{camera_mode_resolution_index}"
            camera_mode_resolutions[resolution_index] = {
                "resolution-index": resolution_index
                , "resolution": (int(ms.group(1)), int(ms.group(2)))
                , "fps": float(ms.group(3))
                , "crop-position": (int(ms.group(4)), int(ms.group(5)))
                , "crop-resolution": (int(ms.group(6)), int(ms.group(7)))}
    
    ctx.obj = { "cameras": cameras }
    
    if not (camerpi_cameras_list or camerpi_modes_list or camerpi_resolutions_list): 
        return
    
    camerpi_cameras_list = [camera.upper() for camera in camerpi_cameras_list.split()]
    show_all_cameras = "ALL" in camerpi_cameras_list
    click.echo(f"{camerpi_cameras_list=}")

    camerpi_modes_list = [mode.upper() for mode in camerpi_modes_list.split(",")]
    show_all_modes = "ALL" in camerpi_modes_list
    click.echo(f"{camerpi_modes_list=}")

    camerpi_resolutions_list = [
        resolution.upper() for resolution in camerpi_resolutions_list.split(",")]
    show_all_resolutions = "ALL" in camerpi_resolutions_list
    click.echo(f"{camerpi_resolutions_list=}")
    
    indents = "\t\t"
    indent_depth = 0
    for camera_index, camera in cameras.items():
        indent_depth = 0
        if show_all_cameras or camera_index in camerpi_cameras_list:
            click.echo(camera_echo(camera))
            indent_depth = 1
            
        if not (camerpi_modes_list or camerpi_resolutions_list):
            continue

        # we're here because user wanted a modes list and/or a resolutions list
        if camerpi_modes_list:
            modes = cameras[camera_index]["modes"]
            for mode_index, mode in modes.items():
                if show_all_modes or mode_index in camerpi_modes_list:
                    click.echo(f"{indents[0:indent_depth]}{mode_echo(mode)}")

                if not camerpi_resolutions_list:
                    # user only wanted modes list
                    continue
                
                # user wanted both the modes list and the resolutions list
                indent_depth += 1
                resolutions = cameras[camera_index]["modes"][mode_index]["resolutions"]
                for resolution_index, resolution in resolutions.items():
                    if show_all_resolutions or resolution_index in camerpi_resolutions_list:
                        click.echo(f"{indents[0:indent_depth]}{resolution_echo(resolution)}")
                indent_depth -= 1

            # we already took care of this camera's modes list and any requested resolutions
            # list so we can just move to the next camera
            continue

        # we're only here because user wanted a resolutions list but not a modes list
        resolutions = cameras[camera_index]["modes"][mode_index]["resolutions"]
        for resolution_index, resolution in resolutions.items():
            if show_all_resolutions or resolution_index in camerpi_resolutions_list:
                click.echo(f"{indents[0:indent_depth]}{resolution_echo(resolution)}")


def camera_echo(camera: dict) -> str:
    echo = f"{camera.get('camera-index', 'C?')}: "
    echo += f"{{dtoverlay: {camera.get('dtoverlay', '??')}, "
    echo += f"sensor-resolution: {camera.get('sensor-resolution', '(?xres?, ?yres?')}, "
    echo += f"device: {camera.get('device', '??')}}}"
    return echo


def mode_echo(mode: dict) -> str:
    echo = f"{mode.get('mode-index', 'M?')}: "
    echo += f"{mode.get('mode', '?mode?')} "
    echo += f"{{bayer-order: {mode.get('bayer-order', '??')}, "
    echo += f"bit-depth: {mode.get('bit-depth', '??')}, "
    echo += f"packing: {mode.get('packing', '??')[-1]}}}"
    return echo


def resolution_echo(resolution: dict) -> str:
    echo = f"{resolution.get('resolution-index', 'R?')}: "
    (xres, yres) = resolution.get('resolution', ('?xres?', '?yres?'))
    echo += f"{xres}x{yres} "
    echo += f"{{fps: {resolution.get('fps', '??')}, "
    echo += f"crop-position: {resolution.get('crop-position', '??')}, "
    echo += f"crop-resolution: {resolution.get('crop-resolution', '??')}}}"
    return echo


@camerpi_grp.command("focus")
@click.argument(
    "focus_time"
    , type=int, default=60, required=False)
@click.option(
    "--camera-index", "-c", "focus_camera_index"
    , help="Index of camera to use (as from --list-cameras)"
    , type=str, default="C0", show_default=True)
@click.option(
    "--mode-index", "-m", "focus_mode_index"
    , help="Index of camera mode to use (as from --list-modes CAMERA)"
    , type=str, default="M0", show_default=True)
@click.option(
    "--resolution-index", "-r", "focus_resolution_index"
    , help="Index of camera mode resolution to use (as from --list-resolutions CAMERA:MODE)"
    , type=str, default="R0", show_default=True)
@click.option(
    "--iso", "-i", "focus_iso"
    , help="Set iso ('gain')"
    , type=int,default=4800, show_default=True)
@click.option(
    "--hflip/--no-hflip", "still_do_hflip"
    , help="Flip image horizontally"
    , is_flag=True, default=False, show_default=True)
@click.option(
    "--vflip/--no-vflip", "still_do_vflip"
    , help="Flip image vertically"
    , is_flag=True, default=False, show_default=True)
@click.pass_obj
def camera_focus_cmd(
        obj
        , focus_time 
        , focus_camera_index
        , focus_mode_index
        , focus_resolution_index
        , focus_iso
        , still_do_hflip
        , still_do_vflip
    ) -> None:
    """Opens a preview window to allow for camera focusing."""
    if not (focus_camera := obj["cameras"].get(focus_camera_index, {})):
        raise RuntimeError(f"no camera found with --camera-index: {focus_camera_index}")
    # click.echo(f"{focus_camera=}")

    if not (focus_mode := focus_camera["modes"].get(focus_mode_index, {})):
        raise RuntimeError(f"no camera mode found with --mode-index: {focus_mode_index}")
    # click.echo(f"{focus_mode=}")

    if not (focus_resolution := focus_mode["resolutions"].get(focus_resolution_index, {})):
        raise RuntimeError(
            f"no camera mode resolution found with --resolution-index: {focus_resolution_index}")
    # click.echo(f"{focus_resolution=}")

    (focus_width, focus_height) = focus_resolution['resolution']
    focus_bit_depth = focus_mode['bit-depth']
    focus_packing = "P" if focus_mode['packing'].endswith("P") else "U"
    focus_framerate = focus_resolution['fps']

    focus_libcamera_mode = f"{focus_width}:{focus_height}:{focus_bit_depth}:{focus_packing}"
    focus_gain = int(min(max(int(focus_iso) / 100, 1), 144))
    focus_time_ms = int(focus_time) * 1000
    focus_cmd = [
        "libcamera-still"
        , "--mode", f"{focus_libcamera_mode}"
        , "-t", f"{focus_time_ms}"
        , "--gain", f"{focus_gain}"
        , "--framerate", f"{focus_framerate}"
        , "--hflip" if still_do_hflip else ""
        , "--vflip" if still_do_vflip else ""
    ]
    click.echo(f"{focus_cmd=}")
    click.echo(f"running as: {' '.join(focus_cmd)}")
    completed_process = subprocess.run(focus_cmd, capture_output=True)
    click.echo(f"{completed_process=}")


@camerpi_grp.command("still")
@click.argument("exposure", type=str)
@click.option(
    "--timeout", "-t", "still_timeout"
    , help="Set preview time in seconds"
    , type=int, default=0, show_default=True)
@click.option(
    "--iso", "-i", "still_iso"
    , help="Set iso ('gain')"
    , type=int, default=100, show_default=True)
@click.option(
    "--raw/--no-raw",
    "still_do_raw",
    is_flag=True,
    default=False,
    show_default=True,
    help="Generate a raw file version of image")
@click.option(
    "--hflip/--no-hflip",
    "still_do_hflip",
    is_flag=True,
    default=False,
    show_default=True,
    help="Flip image horizontally")
@click.option(
    "--vflip/--no-vflip",
    "still_do_vflip",
    is_flag=True,
    default=False,
    show_default=True,
    help="Flip image vertically")
def camera_still_cmd(exposure, still_timeout, still_iso, still_do_raw, still_do_hflip, still_do_vflip):
    """Wrapper for libcamera-still command"""
    still_gain = int(min(max(still_iso / 100, 1), 144))
    still_timeout = int(still_timeout * 1000)
    
    if exposure.startswith("1/"):
        exposure_us = int(1.0/int(exposure[2:]) * 1_000_000)
    elif exposure.endswith('"') or exposure.endswith('s'):
        exposure_us = int(float(exposure[:-1]) * 1_000_000)
    else:
        exposure_us = int(1.0/int(exposure) * 1_000_000)
    
    camera_cmd = [
        "libcamera-still",
        "--mode",
        "8000:6000:10:P",
        #"9152:6944:12:P",
        "-n",
        f"-t {still_timeout}" if still_timeout else "",
        "--shutter",
        f"{exposure_us}",
        "--gain",
        f"{still_gain}",
        "--datetime",
        "--latest",
        "latest.jpg",
        "--raw" if still_do_raw else "",
        "--hflip" if still_do_hflip else "",
        "--vflip" if still_do_vflip else "",
    ]
    click.echo(f"{camera_cmd=}")
    run_subprocess(camera_cmd)


@camerpi_grp.command("timelapse")
@click.option(
    "--exposure-time",
    "-e",
    "timelapse_exposure_time",
    type=str,
    required=True,
    help="Set exposure time in seconds")
@click.option(
    "--pause-time",
    "-p",
    "timelapse_pause_time",
    type=float,
    default=.5,
    show_default=True,
    help="Set pause time between photos, in seconds")
@click.option(
    "--frames",
    "-f",
    "timelapse_frames",
    type=int,
    default=10,
    show_default=True,
    help="Set the number of timelapse photos to take")
@click.option(
    "--iso",
    "-i",
    "timelapse_iso",
    type=int,
    default=100,
    show_default=True,
    help="Set iso ('gain')")
@click.option(
    "--raw/--no-raw",
    "timelapse_do_raw",
    is_flag=True,
    default=True,
    show_default=True,
    help="Generate a raw file version of image")
@click.option(
    "--hflip/--no-hflip",
    "timelapse_do_hflip",
    is_flag=True,
    default=False,
    show_default=True,
    help="Flip image horizontally")
@click.option(
    "--vflip/--no-vflip",
    "timelapse_do_vflip",
    is_flag=True,
    default=False,
    show_default=True,
    help="Flip image vertically")
@click.option(
    "--frame-start",
    "-F",
    "timelapse_frame_start",
    type=int,
    default=1,
    show_default=True,
    help="Set the frame number to use in file names")
def camera_timelapse_cmd(
        timelapse_frames,
        timelapse_iso,
        timelapse_exposure_time,
        timelapse_pause_time,
        timelapse_do_raw,
        timelapse_do_hflip,
        timelapse_do_vflip,
        timelapse_frame_start) -> None:
    """Wrapper for libcamera-still timelapse photography"""
    timelapse_gain = int(min(max(timelapse_iso / 100, 1), 144))
    timelapse_frames = int(max(timelapse_frames, 1))
    timelapse_frame_start = int(max(timelapse_frame_start, 1))
    timelapse_pause_time_ms = int(1000 * max(0.0, timelapse_pause_time))
    if timelapse_exposure_time.startswith("1/"):
        timelapse_exposure_time_us = int(1.0/int(timelapse_exposure_time[2:]) * 1_000_000)
    elif timelapse_exposure_time.endswith('"') or timelapse_exposure_time.endswith('s'):
        timelapse_exposure_time_us = int(float(timelapse_exposure_time[:-1]) * 1_000_000)
    else:
        timelapse_exposure_time_us = int(1.0/int(timelapse_exposure_time) * 1_000_000)
    timelapse_exposure_time = timelapse_exposure_time_us / 1000000.0
    # timelapse_exposure_time = int(timelapse_exposure_time * 1000000)
    timelapse_timeout = \
        ((10 + timelapse_frames * math.ceil(timelapse_exposure_time + timelapse_pause_time)) * 1000)

    camera_cmd = [
        "libcamera-still",
        "--mode",
        "8000:6000:10:P",
        #"9152:6944:12:P",
        #"4056:3040:12:P",
        "-n",
        "-t",
        f"{timelapse_timeout}",
        "--shutter",
        f"{timelapse_exposure_time_us}",
        "--gain",
        f"{timelapse_gain}",
        "-o",
        "timelapse_%04d.jpg",
        "--timelapse",
        f"{timelapse_pause_time_ms}",
        "--vflip" if timelapse_do_vflip else "",
        "--hflip" if timelapse_do_hflip else "",
        "--framestart",
        f"{timelapse_frame_start}",
        "-r" if timelapse_do_raw else "",
    ]
    click.echo(f"{camera_cmd=}")
    run_subprocess(camera_cmd)


def run_subprocess(cmd):
    if not cmd:
        return
    subprocess.run(cmd)


if __name__ == "__main__":
    camerpi_grp()
