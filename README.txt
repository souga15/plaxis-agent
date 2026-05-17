========================================================================
                 PLAXIS AI AGENT - QUICK START GUIDE
========================================================================

Welcome to your Plaxis AI assistant! This tool allows you to control
Plaxis 3D by typing natural language commands. Follow these 4 easy
steps to get it running. No coding knowledge required!

------------------------------------------------------------------------
STEP 1: UNZIP AND OPEN THE FOLDER
------------------------------------------------------------------------
1. Copy the "plaxis-agent" folder to your laptop.
2. Open the folder.

------------------------------------------------------------------------
STEP 2: RUN THE SETUP (Only need to do this ONCE)
------------------------------------------------------------------------
1. Double-click the file named "setup.bat" (it has a gear/gears icon).
2. A black screen will pop up.
   * If Python is NOT on your computer: It will automatically download
     and install it for you! Simply wait and approve any Windows prompts
     that ask for permission. After it finishes, double-click "setup.bat" again.
   * If Python IS on your computer: It will download the necessary
     libraries automatically.
3. Wait until it says "SUCCESS!" and then press any key on your keyboard
   to close the window.

------------------------------------------------------------------------
STEP 3: TURN ON THE PLAXIS SCRIPTING SERVER
------------------------------------------------------------------------
1. Open your Plaxis 3D software.
2. In the top menu, go to: Expert -> Configure remote scripting server
3. Check the box to "Enable" or "Start" the server.
4. Make sure the port is set to "10000" and leave the password blank.
5. Keep Plaxis open in the background.

------------------------------------------------------------------------
STEP 4: RUN THE AI AGENT!
------------------------------------------------------------------------
1. Go back to the "plaxis-agent" folder.
2. Double-click the file named "run.bat".
3. A black screen will open and start the helper server. Keep this open!
4. Open your web browser (Chrome, Edge, Firefox, etc.) and go to:
   http://localhost:8501
5. You will see a beautiful dark chat dashboard. You are ready!
   Type whatever you want to build (e.g. "Create a borehole at 0,0 with 3 layers")
   and watch the AI command Plaxis for you!

------------------------------------------------------------------------
TROUBLESHOOTING
------------------------------------------------------------------------
* "setup.bat" fails to download Python: 
  Go to https://www.python.org/downloads/ and click the yellow "Download" button.
  Run the installer, check the box that says "Add Python to PATH" (Crucial!),
  then click "Install Now". Afterwards, rerun "setup.bat".

Enjoy automating your geotechnical workflows!
========================================================================
