\# 🎮 Steam Library Integrator



A modern, open-source utility designed to automatically scan, organize, and integrate non-Steam games into your Steam library in bulk—complete with official high-resolution artwork fetched directly from Steam's CDN.



\---



\## ✨ Features



\* \*\*🎨 Steam-Inspired Modern UI:\*\* Crafted with a sleek, dark aesthetic and cyan accents matching the latest Steam client interface.

\* \*\*🌐 Bilingual Support:\*\* Instant on-the-fly language toggling between \*\*English\*\* and \*\*Arabic\*\* (with proper bidirectional text alignment).

\* \*\*🖼️ Automated High-Res Artwork:\*\* Automatically queries Steam and downloads official:

&#x20; \* Vertical Library Covers (600x900)

&#x20; \* Hero Background Banners

&#x20; \* Transparent Logos

&#x20; \* Grid Posters

\* \*\*👥 Multi-Account Support:\*\* Auto-detects local Steam installations and active Steam user accounts, with the option to apply shortcuts to a specific user or all accounts simultaneously.

\* \*\*🛡️ Smart Duplicate Prevention:\*\* Scans your existing `shortcuts.vdf` to ensure games already in your library are never duplicated, saving bandwidth and keeping your library clean.

\* \*\*⚡ Automated Steam Process Management:\*\* Safely closes Steam (`steam.exe -shutdown`) to flush configuration data to disk, applies the changes, and restarts Steam automatically upon completion.

\* \*\*🔍 Intelligent Executable Detection:\*\* Advanced heuristics prioritize actual game executables while filtering out redistributables, crash reporters, unins, and anti-cheat launchers.



\---



\## 📥 Download \& Quick Start



1\. Go to the \*\*\[Releases](../../releases)\*\* tab.

2\. Download the latest `SteamLibraryIntegrator\_Clean.zip` package.

3\. Extract the archive anywhere on your system.

4\. Launch `SteamLibraryIntegrator.exe` (No Python installation required).



\---



\## 🚀 Running from Source



If you prefer to run or modify the Python source code directly:



\### Prerequisites

\* Windows 10 / 11

\* Python 3.10+ installed



\### Setup

```bash

\# Clone the repository

git clone \[https://github.com/your-username/SteamLibraryIntegrator.git](https://github.com/your-username/SteamLibraryIntegrator.git)

cd SteamLibraryIntegrator



\# Run the application

python "add game to steam.py"

