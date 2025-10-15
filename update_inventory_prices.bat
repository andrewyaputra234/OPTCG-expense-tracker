@echo off
REM Daily price update script for OPTCG Inventory Tracker
REM Run this script daily to update card prices automatically

cd /d "C:\Users\User\OneDrive\Documents\GitHub\OPTCG-expense-tracker"

echo Starting daily price update...
echo %date% %time% >> price_update.log

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Run the price updater
python price_updater.py update >> price_update.log 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Price update completed successfully >> price_update.log
) else (
    echo Price update failed with error code %ERRORLEVEL% >> price_update.log
)

echo %date% %time% Price update finished >> price_update.log
echo. >> price_update.log