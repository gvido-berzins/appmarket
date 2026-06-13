#!/usr/bin/env bash
# Build signed release APKs for every app (sequential, logs each result).
export JAVA_HOME=/opt/android-studio/jbr
AUTO="-Porg.gradle.java.installations.auto-detect=false"
declare -A DIRS=(
  [plombus]="$HOME/code/plombus/android|-Puniversal"
  [aksess]="$HOME/code/aksess/android|-Puniversal"
  [barcode-scanner]="$HOME/code/appz/apps/barcode-scanner|-Puniversal"
  [namedays-lv]="$HOME/code/appz/apps/namedays-lv|-Puniversal"
  [az-guide]="$HOME/code/az-guide/android|"
)
for name in plombus aksess barcode-scanner namedays-lv az-guide; do
  IFS='|' read -r dir extra <<< "${DIRS[$name]}"
  echo "================ BUILD $name ================"
  ( cd "$dir" && ./gradlew :app:assembleRelease $extra $AUTO --console=plain 2>&1 | tail -8 )
  echo "---- $name release APKs ----"
  find "$dir/app/build/outputs/apk/release" -name "*.apk" 2>/dev/null
done
echo "================ DONE ================"
