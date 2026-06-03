@echo off
echo ==================================================
echo [STATUS] Salim Botaem Auto Sync Tool Running...
echo ==================================================

echo.
echo [STEP 1] Downloading sheet data and updating password...
python inject_sheet_data.py
if errorlevel 1 goto DATA_ERROR

echo.
echo [STEP 2] Uploading updated files to GitHub...
git add .
git commit -m "Auto sync: Update data and passcode config"
git push
if errorlevel 1 goto GIT_ERROR

echo.
echo ==================================================
echo [SUCCESS] Update and Deployment completed!
echo Please refresh your website in 1-2 minutes.
echo ==================================================
pause
exit

:DATA_ERROR
echo.
echo [ERROR] Failed to run inject_sheet_data.py.
echo Please check your python installation or sheet connection.
pause
exit

:GIT_ERROR
echo.
echo [ERROR] Failed to push to GitHub.
echo Please check your internet connection or git login status.
pause
exit
