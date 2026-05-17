# 🤖 PLAXIS AI AGENT — QUICK START GUIDE

Welcome to the **PLAXIS AI Automation Agent**! This application allows you to control PLAXIS 3D by simply typing natural language commands (e.g., *"Create a borehole at the origin with 3 soil layers"* or *"Get structural forces for Plate_1"*). 

**No coding or programming knowledge is required to run this!** Follow the simple steps below to get it set up on your machine.

---

## 🚀 How to Run (4 Easy Steps)

### 1️⃣ Download the Code
1. Click the green **`Code`** button at the top of this GitHub page.
2. Select **`Download ZIP`**.
3. Once downloaded, extract (unzip) the folder anywhere on your computer (e.g., your Desktop).

### 2️⃣ Run the Installer (Only need to do this ONCE)
1. Open the extracted `plaxis-agent` folder.
2. Double-click the file named **`setup.bat`** (it has a gears/settings icon).
3. A black screen will pop up:
   * **If Python is NOT on your computer:** It will automatically download and install it for you! Simply wait and approve any Windows prompts asking for permission. After it finishes, double-click `setup.bat` again.
   * **If Python IS on your computer:** It will automatically configure all necessary libraries.
4. Follow any on-screen prompts to configure your API Keys (Gemini/Groq) if you have them.
5. Wait until it says `SUCCESS!` and then press any key to close the window.

### 3️⃣ Turn on the PLAXIS Remote Scripting Server
1. Open your **PLAXIS 3D** software.
2. In the top menu, navigate to: **`Expert`** ➡️ **`Configure remote scripting server`**.
3. Check the box to **`Enable`** or **`Start`** the server.
4. Ensure the port is set to **`10000`** and leave the password blank.
5. Keep PLAXIS open in the background!

### 4️⃣ Launch your AI Assistant!
1. Go back to your `plaxis-agent` folder.
2. Double-click the file named **`run.bat`**.
3. A black helper screen will open. **Keep this open in the background!**
4. Open your web browser (Chrome, Edge, Firefox) and go to:
   👉 **`http://localhost:8501`**
5. You will see a beautiful dark chat dashboard. Start typing your prompts and watch the AI build models and query results in PLAXIS 3D!

---

## 🛠️ Troubleshooting

* **`setup.bat` fails to install Python:** 
  Download and install Python manually from [python.org/downloads](https://www.python.org/downloads/). 
  > ⚠️ **CRITICAL:** During manual installation, make sure to check the box that says **`Add Python to PATH`** before clicking "Install Now". Afterwards, re-run `setup.bat`.

* **Connection Error: "Not connected to Plaxis Input server":**
  Ensure that you started the remote scripting server in PLAXIS 3D (Expert menu) and that port `10000` is active.

---

*Enjoy automating your geotechnical workflows!* 🚀
