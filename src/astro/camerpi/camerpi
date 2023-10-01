#!/usr/bin/python

import click
import math
import subprocess

@click.group()
def camerpi():
    """Wrapper for libcamera-* commands"""
    pass


@camerpi.command("focus")
@click.option(
    "--resolution", "-r", "focus_resolution"
    , help="Set sensor resolution to W:H"
    , default="1333:990", show_default=True)
@click.option(
    "--bits", "-b", "focus_bits"
    , help="Set sensor channel bit depth"
    , default="10", show_default=True)
@click.option(
    "--packed", "-p", "focus_is_packed"
    , help="Set bit packing on"
    , default=True, show_default=True)
@click.option(
    "--focus-time", "-f", "focus_time"
    , help="Set focus time in seconds"
    , type=int, default=60, show_default=True)
@click.option(
    "--iso", "-i", "focus_iso"
    , help="Set iso ('gain')"
    , type=int,default=4800, show_default=True)
@click.option(
    "--metering", "-m", "focus_metering"
    , help="Set focus metering"
    , default="average", show_default=True)
@click.option(
    "--framerate", "focus_framerate"
    , help="Set focus framerate"
    , type=int, default=24, show_default=True)
@click.option(
    "--hflip/--no-hflip", "still_do_hflip"
    , help="Flip image horizontally"
    , is_flag=True, default=False, show_default=True)
@click.option(
    "--vflip/--no-vflip", "still_do_vflip"
    , help="Flip image vertically"
    , is_flag=True, default=False, show_default=True)
def camera_focus_cmd(
        focus_resolution
        , focus_bits
        , focus_is_packed
        , focus_time 
        , focus_iso
        , focus_metering
        , focus_framerate
        , still_do_hflip
        , still_do_vflip
    ) -> None:
    """Opens a preview window to allow for camera focusing."""
    focus_mode = f"{focus_resolution}:{focus_bits}:{'P' if focus_is_packed else 'U'}"
    focus_gain = int(min(max(int(focus_iso) / 100, 1), 144))
    focus_time_ms = focus_time * 1000
    camera_cmd = [
        "libcamera-still",
        "--mode",
        f"{focus_mode}",
        "-t",
        f"{focus_time_ms}",
        "--gain",
        f"{focus_gain}",
        "--framerate",
        f"{focus_framerate}",
        "--metering",
        f"{focus_metering}",
        "--hflip" if still_do_hflip else "",
        "--vflip" if still_do_vflip else "",
    ]
    # cmd = f"libcamera-still --mode {focus_mode} --qt-preview -t {focus_time} --gain {focus_gain}"
    click.echo(f"{camera_cmd=}")
    run_subprocess(camera_cmd)


@camerpi.command("still")
@click.argument("exposure", type=str)
@click.option(
    "--timeout",
    "-t",
    "still_timeout",
    type=int,
    default=0,
    show_default=True,
    help="Set preview time in seconds")
@click.option(
    "--iso",
    "-i",
    "still_iso",
    type=int,
    default=100,
    show_default=True,
    help="Set iso ('gain')")
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


@camerpi.command("timelapse")
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
    camerpi()
