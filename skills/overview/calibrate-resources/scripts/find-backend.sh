#!/usr/bin/env bash
# Find a self-hosted Calibrate's backend API host from its web (frontend) address.
#
# The web app is compiled with its API host baked into the JavaScript, so we
# fetch the page + its JS assets and pull out URLs that live on a different host
# than the front end. Prints the best-guess API host first, then other
# candidates (one per line). Confirm the top hit with the user before using it:
#   calibrate configure --no-interactive --server-url https://<host>
#
# Usage: find-backend.sh <web-address>      e.g. find-backend.sh calibrate.example.org
set -euo pipefail

raw="${1:-}"
[ -n "$raw" ] || { echo "usage: find-backend.sh <web-address>" >&2; exit 2; }

# Normalize: ensure a scheme, drop any trailing slash.
case "$raw" in
  http://*|https://*) url="$raw" ;;
  *)                  url="https://$raw" ;;
esac
url="${url%/}"
front_host="$(printf '%s' "$url" | sed -E 's#^https?://([^/]+).*#\1#')"

html="$(curl -fsSL "$url/" 2>/dev/null || true)"
[ -n "$html" ] || { echo "could not fetch $url" >&2; exit 1; }

# Asset URLs the page references: src=/href= .js/.json, plus Next.js chunk paths.
assets="$( {
  printf '%s' "$html" | grep -oE '(src|href)="[^"]+\.(js|json)(\?[^"]*)?"' \
    | sed -E 's/^(src|href)="//; s/"$//';
  printf '%s' "$html" | grep -oE '/_next/static/[A-Za-z0-9_./-]+\.js';
} | sort -u )"

fetch() { # fetch an asset that may be absolute or relative to the site
  case "$1" in
    http://*|https://*) curl -fsSL "$1"     2>/dev/null || true ;;
    /*)                 curl -fsSL "$url$1" 2>/dev/null || true ;;
    *)                  curl -fsSL "$url/$1" 2>/dev/null || true ;;
  esac
}

corpus="$html"
while IFS= read -r a; do
  [ -n "$a" ] || continue
  corpus="$corpus
$(fetch "$a")"
done <<EOF
$assets
EOF

# Candidate hosts = every dotted http(s) host in the corpus, minus the front end
# and common third parties.
cands="$(printf '%s' "$corpus" \
  | grep -oE 'https?://[a-zA-Z0-9._-]+' \
  | sed -E 's#^https?://##' \
  | grep -E '\.[a-zA-Z]{2,}$' \
  | sort -u \
  | grep -viE "^(www\.)?(${front_host}|localhost|127\.0\.0\.1)$" \
  | grep -viE '(vercel|google|gstatic|googleapis|fonts|sentry|cloudflare|jsdelivr|unpkg|cdn\.|schema\.org|w3\.org|github|npmjs|posthog|segment|intercom|stripe|doubleclick)' \
  || true )"

# A self-hosted backend almost always sits on the front end's parent domain
# (calibrate.example.org -> *.example.org). Rank those first, and within each
# group put backend/api-looking hosts on top.
parent="$(printf '%s' "$front_host" | sed -E 's/^[^.]+\.//')"
pat="\.$(printf '%s' "$parent" | sed 's/\./\\./g')$"
group() { printf '%s\n' "$1" | { grep -iE 'backend|api' || true; printf '%s\n' "$1" | grep -viE 'backend|api' || true; } | awk 'NF'; }
same="$(printf '%s\n' "$cands" | grep -iE "$pat" || true)"
other="$(printf '%s\n' "$cands" | grep -viE "$pat" || true)"
ranked="$( { group "$same"; group "$other"; } | awk 'NF && !seen[$0]++' )"

[ -n "$ranked" ] || {
  echo "no backend candidate found — inspect the site's network calls in DevTools, or ask whoever deployed it" >&2
  exit 1
}

# Best guess on stdout; the rest to stderr as context in case it's wrong.
best="$(printf '%s\n' "$ranked" | head -1)"
rest="$(printf '%s\n' "$ranked" | tail -n +2)"
printf '%s\n' "$best"
[ -n "$rest" ] && printf 'other candidates (confirm with the user if the above looks wrong):\n%s\n' "$rest" >&2
exit 0
