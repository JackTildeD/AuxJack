#!/usr/bin/env python3
# --- 80 cols ------------------------------------------------------------------
# Jack~D

import discord
import asyncio
import re
import os
import sys
import math
from discord.ext import commands

# Required external software: youtube-dl, ffmpeg
# Required python modules: dispord.py, asyncio
# Token for discord bot in file "token"
# Developer user ID in file "dev_id"

# Gets directory of running script
def get_script_directory():
   path = os.path.realpath(sys.argv[0])
   if os.path.isdir(path):
      return path
   else:
      return os.path.dirname(path)

# Asynchronus run shell command
async def run_command(cmd):
   proc = await asyncio.create_subprocess_shell(
      cmd,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE
      )
   stdout, stderr = await proc.communicate()
   return (
      proc.returncode,
      stdout.decode(),
      stderr.decode()
      )

# Main bot class
class main(discord.Client):
   
   # Initialization
   def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.actually_ready = False
      self.dev = None # Assigned later
      self.job_lock = asyncio.Lock()
      self.job_queue = []
      # Adds my_loop function to event loop
      self.loop.create_task(self.my_loop())
      return
   
   # Close connection and end program
   async def shutdown(self):
      self.actually_ready = False
      await self.close() # Program ends here
      return
   
   # Add message to job queue
   async def add_to_queue(self, cmd, message):
      async with self.job_lock:
         self.job_queue.append([cmd, message])
      return
   
   # Validates input for auxclip function
   # Returns true if input is invalid
   async def invalidate_auxclip(self, message):
      try:
         # Function arguments list
         args = [i.strip() for i in message.content.strip()[8:].split(",")]
         print("{" + str(args) + "}")
         # Regex for YouTube video IDs
         youtube_id = re.compile(
            "^[a-zA-Z0-9\-\_]{11}[a-zA-Z0-9\-\_]*$"
            )
         # Regex for timecodes
         timecode = re.compile("^\d\d:\d\d$")
         if len(args) != 3:
            return True
         if not youtube_id.match(args[0]):
            return True
         if not timecode.match(args[1]):
            return True
         if not timecode.match(args[2]):
            return True
         for i in range(1, 3):
            args[i] = [int(j) for j in args[i].split(":")]
            for j in args[i]:
               if 60 <= j:
                  return True
         start_seconds = args[1][0] * 60 + args[1][1]
         end_seconds = args[2][0] * 60 + args[2][1]
         duration_seconds = end_seconds - start_seconds
         if duration_seconds <= 0:
            return True
      except:
         print("HereE")
         return True
      return False
   
   # Downloads a video using youtube-dl
   # Create a smaller clip based on timecodes with ffmpeg
   async def auxclip(self, message):
      try:
         # Function arguments list
         args = [i.strip() for i in message.content.strip()[8:].split(",")]
         # Script directory
         dir = get_script_directory()
         # Prepare tmp directory
         returncode, stdout, stderr = await run_command(
f"""
cd "{dir}"
if [ ! -d "tmp" ]; then mkdir "tmp"; fi
cd "tmp"
ls --all -1 \
| grep --extended-regexp --invert-match "^\.\.?$" \
| xargs --no-run-if-empty rm
""")
         if returncode != 0:
            await message.channel.send(
               f"I’m sorry <@{message.author.id}>, "
               + "the shell encountered an error"
               )
            print(str(stderr))
            return
         await asyncio.sleep(0) # Prevent blocking
         # Download video with youtube-dl
         returncode, stdout, stderr = await run_command(
f"""
cd "{dir}"
cd "tmp"
youtube-dl https://www.youtube.com/watch?v={args[0]} \
--no-color --no-playlist --max-filesize 500m \
-f "bestvideo[ext=webm][height<480]+bestaudio[ext=webm]" \
-o "video.%(ext)s"
""")
         if returncode != 0:
            await message.channel.send(
               f"I’m sorry <@{message.author.id}>, "
               + "`youtube-dl` encountered an error"
               )
            print(str(stderr))
            return
         await asyncio.sleep(0) # Prevent blocking
         # Get output filename
         returncode, stdout, stderr = await run_command(
f"""
cd "{dir}"
cd "tmp"
ls -1 | grep "^video[.][^.]*$" | sed 1q | sed "s|video|clip|"
""")
         if returncode != 0:
            await message.channel.send(
               f"I’m sorry <@{message.author.id}>, "
               + "the shell encountered an error"
               )
            print(str(stderr))
            return
         output_file = stdout.strip()
         start_time = args[1]
         for i in range(1, 3):
            args[i] = [int(j) for j in args[i].split(":")]
         await asyncio.sleep(0) # Prevent blocking
         start_seconds = args[1][0] * 60 + args[1][1]
         end_seconds = args[2][0] * 60 + args[2][1]
         await asyncio.sleep(0) # Prevent blocking
         duration_seconds = end_seconds - start_seconds
         # Duration in string format
         duration = f"{math.floor(duration_seconds / 60):02d}:"
         duration += f"{duration_seconds % 60:02d}"
         # Create clip with ffmpeg
         returncode, stdout, stderr = await run_command(
f"""
cd "{dir}"
cd "tmp"
input_file=$(ls -1 | grep "^video[.][^.]*$" | sed 1q)
ffmpeg -i $input_file -ss 00:{start_time} -t 00:{duration} \
-async 1 {output_file}
""")
         if returncode != 0:
            await message.channel.send(
               f"I’m sorry <@{message.author.id}>, "
               + "`ffmpeg` encountered an error"
               )
            print(str(stderr))
            return
         await asyncio.sleep(0) # Prevent blocking
         await message.channel.send(
            f"Here is your clip <@{message.author.id}>",
            file=discord.File(f"{dir}/tmp/{output_file}".strip())
            )
      except:
         await message.channel.send(
            f"I’m sorry <@{message.author.id}>, "
            + "an unexpected exception occurred"
            )
      return
   
   # Job execution loop
   async def my_loop(self):
      await self.wait_until_ready()
      while self.is_ready():
         if self.actually_ready:
            async with self.job_lock:
               # Get first job
               if 0 < len(self.job_queue):
                  job = self.job_queue[0]
               else:
                  job = None
            await asyncio.sleep(0)
            if job != None:
               # auxclip job
               if job[0] == "auxclip":
                  await self.auxclip(job[1])
                  async with self.job_lock:
                     # Remove finised job
                     self.job_queue.pop(0)
         await asyncio.sleep(5) # Prevent blocking
      return
   
   # Runs when connected
   async def on_ready(self):
      # Get developer user
      self.dev = self.get_user(int(
         open("dev_id", "r").read().strip()
         ))
      print("Connected and ready")
      self.actually_ready = True
      return
   
   # Runs when a message is detected anywhere
   async def on_message(self, message):
      temp = message.content.lower().strip()
      if not self.actually_ready:
         return
      if message.author.bot:
         return
      if message.author.id == self.dev.id and \
         temp.startswith("!shutdown"):
         await message.channel.send("Shutting down")
         await self.shutdown() # Program ends here
         return
      if temp.startswith("auxclip "):
         if await self.invalidate_auxclip(message):
            await message.channel.send("Invalid input")
         else:
            await message.channel.send("Adding to job queue")
            await self.add_to_queue("auxclip", message)
         return
      return

auxjack = main()
auxjack.run(open("token", "r").read().strip())

# END OF LINE

