#!/usr/bin/python

import click
import math
import re
import subprocess

from pprint import pp

@click.group("camerpi")
@click.pass_context
def camerpi_grp(ctx):
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
        
        if ms := re.match(r"Modes: '(S([RGB]{4})(\d+)_(\w+))' : ", row):
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
            row = row[len(ms.group(0)):]
        
        if ms := re.match(
            r"(\d+)x(\d+) \[(\d+\.\d+) fps - \((\d+), (\d+)\)/(\d+)x(\d+) crop\]"
            , row
        ):  # found a resolution mode entry
            camera_mode_resolution_index += 1
            resolution_index = f"R{camera_mode_resolution_index}"
            camera_mode_resolutions[resolution_index] = {
                "key": resolution_index
                , "resolution": (int(ms.group(1)), int(ms.group(2)))
                , "fps": float(ms.group(3))
                , "crop-position": (int(ms.group(4)), int(ms.group(5)))
                , "crop-resolution": (int(ms.group(6)), int(ms.group(7)))}
    
    ctx.obj = { "cameras": cameras }


@camerpi_grp.group("list", invoke_without_command=True)
@click.option(
    "--show_cameras", "-c", "show_cameras"
    , help="Show all available cameras."
    , is_flag=True, default=True, show_default=False)
@click.option(
    "--show_modes", "-m", "show_modes"
    , help="Show all modes supported by available cameras."
    , is_flag=True, default=True, show_default=False)
@click.option(
    "--show_resolutions", "-r", "show_resolutions"
    , help="Show all modes supported by available cameras."
    , is_flag=True, default=True, show_default=False
)
@click.pass_context
def camerpi_list_grp(ctx: click.Context, show_cameras, show_modes, show_resolutions):
    click.echo(f"{ctx.invoked_subcommand=}")
    click.echo(f"{ctx.parent.info_name=}")
    click.echo(f"{ctx.args=}")
    if ctx.invoked_subcommand is None:
        if show_cameras:
            ctx.invoke(
                camerpi_list_cameras_cmd
                , show_modes=show_modes
                , show_resolutions=show_resolutions)
        elif show_modes:
            ctx.invoke(camerpi_list_modes_cmd, show_resolutions=show_resolutions)
        elif show_resolutions:
            ctx.invoke(camerpi_list_resolutions_cmd)
        else:
            click.echo(ctx.get_help())


@camerpi_list_grp.command("cameras")
@click.option(
    "-C", "cameras_set"
    , help="Specify camera to list information about (use a separate -C for each camera)."
    , type=int, multiple=True
)
@click.option(
    "--show_modes", "-m"
    , help="Show all modes supported by specified cameras."
    , is_flag=True, default=True, show_default=True
)
@click.option(
    "--show_resolutions", "-r"
    , help="Show all resolutions supported by specified cameras' modes."
    , is_flag=True, default=True, show_default=True
)
@click.pass_obj
def camerpi_list_cameras_cmd(obj, cameras_set, show_modes, show_resolutions):
    """Display information about available cameras.
    
    If no camera is specified by a -C option then all available cameras are listed.
    """
    cameras = dict(obj['cameras'])
    cameras_set = sorted(set({f"C{camera}" for camera in cameras_set} or cameras.keys()))
    for camera_index in cameras_set:
        try:
            camera = cameras[camera_index]
            click.echo(camera_echo(camera))
            if show_modes:
                modes = camera['modes'].values()
                for mode in modes:
                    click.echo(f"    {mode_echo(mode)}")
                    if show_resolutions:
                        resolutions = mode['resolutions'].values()
                        for resolution in resolutions:
                            click.echo(f"        {resolution_echo(resolution)}")
        except KeyError:
            click.echo(f"no camera '{camera_index}' found", err=True)
            continue


@camerpi_list_grp.command("modes")
@click.option(
    "-M", "modes_set"
    , help="Specify camera mode to list information about (use separate -M for each mode)"
    , type=int, multiple=True
)
@click.option(
    "--show-resolutions", "-r"
    , help="Show all resolutions supported by specified modes."
    , is_flag=True, default=True, show_default=True
)
@click.pass_obj
def camerpi_list_modes_cmd(obj, modes_set, show_resolutions):
    """Display information about supported modes on available cameras.
    
    If no mode is specified by the -M option then all available modes supported by each 
    camera are listed.
    """
    cameras = obj['cameras'].values()
    modes = {}
    for camera in cameras:
        modes |= camera['modes']
    mode_indexes = sorted(set({f"M{mode}" for mode in set(modes_set)} or modes.keys()))
    for mode_index in mode_indexes:
        try:
            mode = modes[mode_index]
            click.echo(f"{mode_echo(mode)}")
            if show_resolutions:
                resolutions = mode['resolutions'].values()
                for resolution in resolutions:
                    click.echo(f"    {resolution_echo(resolution)}")
        except KeyError:
            click.echo(f"no mode '{mode_index}' found", err=True)
                

@camerpi_list_grp.command("resolutions")
@click.option(
    "-R", "resolutions_set"
    , help="Specify resolution to list information about (use a separate -R for each resolution)"
    , type=int, multiple=True
)
@click.pass_obj
def camerpi_list_resolutions_cmd(obj, resolutions_set):
    """Display information about supported resolutions on available camera modes.
    
    If no resolution is specified by the -R option then all available resolutions
    supported by each camera mode are listed.
    """
    cameras = obj['cameras'].values()
    resolutions = {}
    for camera in cameras:
        for mode in camera['modes'].values():
            resolutions |= mode['resolutions']
    resolution_indexes = sorted(set({f"R{resolution}" for resolution in set(resolutions_set)} or resolutions.keys()))
    for resolution_index in resolution_indexes:
        try:
            resolution = resolutions[resolution_index]
            click.echo(f"{resolution_echo(resolution)}")
        except KeyError:
            click.echo(f"no resolution '{resolution_index}' found", err=True)


@camerpi_list_grp.command("config")
@click.pass_obj
def camerpi_list_config_cmd(cameras):
    pass


def camera_echo(camera: dict) -> str:
    echo = f"{camera.get('camera-index', 'C?')}: "
    echo += f"{{dtoverlay: {camera.get('dtoverlay', '??')}, "
    (xres, yres) = camera.get('sensor-resolution', ('?xres?', '?yres?'))
    echo += f"sensor-resolution: {xres}x{yres}, "
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
    echo = f"{resolution.get('key', 'R?')}: "
    (xres, yres) = resolution.get('resolution', ('?xres?', '?yres?'))
    echo += f"{xres}x{yres} "
    echo += f"{{fps: {resolution.get('fps', '??'):.2f}, "
    echo += f"crop-position: {resolution.get('crop-position', '??')}, "
    (xres, yres) = resolution.get('crop-resolution', ('?xres?', '?yres?'))
    echo += f"crop-resolution: {xres}x{yres}}}"
    return echo


@camerpi_grp.command("focus")
@click.argument(
    "focus_time"
    , type=int, default=60, required=False)
@click.option(
    "-C", "camera_index"
    , help="Set camera to use (as from '--show-cameras')"
    , type=int, default=0, show_default=False)
@click.option(
    "-M", "mode_index"
    , help="Set camera mode to use (as from '--show-modes')"
    , type=int, default=0, show_default=False)
@click.option(
    "-R", "resolution_index"
    , help="Set camera mode resolution to use (as from '--show-resolutions')"
    , type=int, default=0, show_default=False)
@click.option(
    "--iso", "-i", "focus_iso"
    , help="Set iso ('gain')"
    , type=int, default=4800, show_default=False)
@click.option(
    "--hflip", "still_hflip"
    , help="Flip image horizontally"
    , is_flag=True, default=True, show_default=False)
@click.option(
    "--vflip", "still_vflip"
    , help="Flip image vertically"
    , is_flag=True, default=True, show_default=False)
@click.option(
    "--cameras", "-c", "show_cameras"
    , help="Show all cameras available."
    , is_flag=True, default=False)
@click.option(
    "--modes", "-m", "show_modes"
    , help="Show all modes supported by all available cameras."
    , is_flag=True, default=False)
@click.option(
    "--resolutions", "-r", "show_resolutions"
    , help="Show all resolutions supported by all available camera modes."
    , is_flag=True, default=False)
@click.pass_obj
def camera_focus_cmd(
        obj
        , focus_time 
        , camera_index
        , mode_index
        , resolution_index
        , focus_iso
        , still_hflip
        , still_vflip
        , show_cameras
        , show_modes
        , show_resolutions) -> None:
    """Opens a preview window to allow for camera focusing."""

    if show_cameras or show_modes or show_resolutions:
        click.get_current_context().invoke(
            camerpi_list_grp
            , show_cameras=show_cameras
            , show_modes=show_modes
            , show_resolutions=show_resolutions)
    # elif show_modes:
    #     click.get_current_context().invoke(
    #         camerpi_list_modes_cmd
    #         , show_resolutions=show_resolutions)
    # elif show_resolutions:
    #     click.get_current_context().invoke(camerpi_list_resolutions_cmd)
    
    # convert indexes to keys
    camera_key = f"C{camera_index}"
    mode_key = f"M{mode_index}"
    resolution_key = f"R{resolution_index}"
    
    if not (focus_camera := obj["cameras"].get(camera_key, {})):
        raise RuntimeError(f"camera -{camera_key} not found")
    # click.echo(f"{focus_camera=}")

    if not (focus_mode := focus_camera["modes"].get(mode_key, {})):
        raise RuntimeError(f"mode -{mode_key} not found")
    # click.echo(f"{focus_mode=}")

    if not (focus_resolution := focus_mode["resolutions"].get(resolution_key, {})):
        raise RuntimeError(
            f"resolution -{resolution_key} not found")
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
        , "--hflip" if still_hflip else ""
        , "--vflip" if still_vflip else ""
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
