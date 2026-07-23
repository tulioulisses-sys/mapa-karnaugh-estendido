#!/usr/bin/env bash
set -euo pipefail

: "${SUPABASE_URL:?Informe SUPABASE_URL no serviço estático.}"
: "${SUPABASE_PUBLISHABLE_KEY:?Informe SUPABASE_PUBLISHABLE_KEY no serviço estático.}"
: "${API_BASE_URL:?Informe API_BASE_URL no serviço estático.}"

FLUTTER_CHANNEL="${FLUTTER_CHANNEL:-stable}"
FLUTTER_SDK_DIR="${FLUTTER_SDK_DIR:-${HOME}/flutter-sdk}"

if [[ ! -x "${FLUTTER_SDK_DIR}/bin/flutter" ]]; then
  git clone \
    --depth 1 \
    --branch "${FLUTTER_CHANNEL}" \
    https://github.com/flutter/flutter.git \
    "${FLUTTER_SDK_DIR}"
fi

export PATH="${FLUTTER_SDK_DIR}/bin:${PATH}"

flutter config --enable-web

cd mobile
flutter pub get
flutter build web \
  --release \
  "--dart-define=SUPABASE_URL=${SUPABASE_URL}" \
  "--dart-define=SUPABASE_PUBLISHABLE_KEY=${SUPABASE_PUBLISHABLE_KEY}" \
  "--dart-define=API_BASE_URL=${API_BASE_URL}"
