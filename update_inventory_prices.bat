@echo off
echo Starting Daily Price Update...
echo.

:: Change to the project directory
cd /d "C:\Users\User\OneDrive\Documents\GitHub\OPTCG-expense-tracker"

:: Run the price updater
python price_updater.py

echo.
echo Price update completed at %DATE% %TIME%
echo.

:: Optional: Add logging
echo %DATE% %TIME% - Price update completed >> price_update.log

:: Keep the window open for a few seconds to see results
timeout /t 5

:: Uncomment the next line if you want to keep the window open until user presses a key
:: pause
