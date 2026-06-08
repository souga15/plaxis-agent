# First-Time Setup

This guide is for someone who does not write code and just wants to run the app.

## Fastest Option

Use `dist\PlaxisAI.exe` if it is available.

1. Double-click `PlaxisAI.exe`
2. Open `PLAXIS 3D`
3. In PLAXIS, go to `Expert -> Configure remote scripting server`
4. Enable remote scripting with:
   `Input: 10000`
   `Output: 10001`
   `Password: blank`
5. In the app, open the `Settings` tab
6. Paste an AI API key and click `Save & Apply Changes`
7. Go back to `AI Chat` and type a simple request like:
   `Start a new project`

## If You Are Running From This Folder

Use these two files:

- `setup.bat`
- `run.bat`

### First time only

1. Double-click `setup.bat`
2. Wait for installation to finish
3. Follow any on-screen prompts

### Every time after that

1. Open `PLAXIS 3D`
2. Enable the remote scripting server:
   `Expert -> Configure remote scripting server`
3. Confirm:
   `Input: 10000`
   `Output: 10001`
   `Password: blank`
4. Double-click `run.bat`
5. If the browser does not open by itself, open:
   `http://127.0.0.1:8501`

## Before Sending Commands

Make sure these are true:

- PLAXIS is open
- Remote scripting is enabled
- An API key is saved in the app
- The left sidebar shows green dots for Input and Output when connected

## If Something Fails

- `Command is not recognized as a global command`:
  PLAXIS may still be on the Start Page, or the connection may not be ready yet.
- `Not connected to PLAXIS`:
  Check the remote scripting ports and confirm PLAXIS is still open.
- The AI replies but does nothing:
  Open the `Settings` tab and confirm at least one provider is active.

## Best First Test

After everything is open, try these in order:

1. `Start a new project`
2. `List all phases`
3. `Create a simple borehole at 0,0 with two layers`

If step 1 works but step 3 fails, the next thing to check is PLAXIS version and scripting compatibility.
