
#!/usr/bin/env bash
# setup_git.sh: asciireveal projesini GitHub'a yüklemek için git işlemlerini yapar.
#
# Yaptıkları:
#   1. README'lerdeki kullanıcı adı yer tutucularını gerçek adınla değiştirir
#   2. pyproject.toml'a [project.urls] ekler (yoksa)
#   3. git init, ilk commit, main dalı
#   4. GitHub deposunu bağlar (gh kuruluysa depoyu da oluşturur) ve push eder
#
# Kullanım:
#   ./setup_git.sh -u KULLANICI_ADIN
#   ./setup_git.sh -u KULLANICI_ADIN -s          # SSH ile bağlan
#   ./setup_git.sh -u KULLANICI_ADIN -p          # gh ile ÖZEL (private) depo oluştur
#   ./setup_git.sh -h                            # tüm seçenekler
#
# Betik tekrar çalıştırılabilir: yapılmış adımları atlar.
 
set -euo pipefail
 
# ---------------------------------------------------------------- yardımcılar
if [ -t 1 ]; then
  B=$'\033[1m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
else
  B=""; G=""; Y=""; R=""; N=""
fi
info() { printf '%s==>%s %s\n' "$G$B" "$N" "$*"; }
warn() { printf '%s!!%s  %s\n' "$Y$B" "$N" "$*" >&2; }
die()  { printf '%shata:%s %s\n' "$R$B" "$N" "$*" >&2; exit 1; }
 
usage() {
  cat <<'EOF'
Kullanım: ./setup_git.sh [seçenekler]
 
  -u KULLANICI   GitHub kullanıcı adın (verilmezse sorulur)
  -r DEPO        Depo adı (varsayılan: asciireveal)
  -m MESAJ       İlk commit mesajı (varsayılan: "İlk sürüm: asciireveal 0.1.0")
  -s             Uzak adres olarak SSH kullan (git@github.com:...) [varsayılan: HTTPS]
  -p             gh ile depoyu ÖZEL (private) oluştur [varsayılan: herkese açık]
  -R URL         Uzak adresi elle ver (GitHub yerine başka bir remote için)
  -y             Soru sorma, her şeye "evet" de
  -h             Bu yardımı göster
EOF
}
 
ask_yes() { # ask_yes "soru" -> 0 evet / 1 hayır
  [ "$ASSUME_YES" = 1 ] && return 0
  local a
  read -r -p "$1 [E/h] " a || true
  case "${a:-e}" in [eEyY]*) return 0 ;; *) return 1 ;; esac
}
 
# ---------------------------------------------------------------- seçenekler
GH_USER=""; REPO_NAME="asciireveal"; COMMIT_MSG="İlk sürüm: asciireveal 0.1.0"
USE_SSH=0; PRIVATE=0; REMOTE_URL=""; CUSTOM_REMOTE=0; ASSUME_YES=0
 
while getopts "u:r:m:spR:yh" opt; do
  case "$opt" in
    u) GH_USER="$OPTARG" ;;
    r) REPO_NAME="$OPTARG" ;;
    m) COMMIT_MSG="$OPTARG" ;;
    s) USE_SSH=1 ;;
    p) PRIVATE=1 ;;
    R) REMOTE_URL="$OPTARG"; CUSTOM_REMOTE=1 ;;
    y) ASSUME_YES=1 ;;
    h) usage; exit 0 ;;
    *) usage; exit 1 ;;
  esac
done
 
# Betik hangi dizinden çağrılırsa çağrılsın proje köküne geç
cd "$(dirname "${BASH_SOURCE[0]}")"
[ -f pyproject.toml ] || die "pyproject.toml bulunamadı; betik proje kök klasöründe olmalı."
command -v git >/dev/null 2>&1 || die "git kurulu değil. Arch'ta: sudo pacman -S git"
 
if [ -z "$GH_USER" ] && [ -z "$REMOTE_URL" ]; then
  read -r -p "GitHub kullanıcı adın: " GH_USER
fi
if [ -z "$REMOTE_URL" ]; then
  [[ "$GH_USER" =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$ ]] \
    || die "Geçersiz GitHub kullanıcı adı: '$GH_USER'"
fi
[[ "$REPO_NAME" =~ ^[A-Za-z0-9._-]+$ ]] || die "Geçersiz depo adı: '$REPO_NAME'"
 
if [ -z "$REMOTE_URL" ]; then
  if [ "$USE_SSH" = 1 ]; then
    REMOTE_URL="git@github.com:${GH_USER}/${REPO_NAME}.git"
  else
    REMOTE_URL="https://github.com/${GH_USER}/${REPO_NAME}.git"
  fi
fi
WEB_URL="https://github.com/${GH_USER}/${REPO_NAME}"
 
# ---------------------------------------------------------------- 1) yer tutucular
if [ -n "$GH_USER" ]; then
  if grep -qE '<your-username>|<kullanici-adin>|\(README\.tr\.md\)' README.md README.tr.md 2>/dev/null; then
    info "README dosyalarında kullanıcı adı yerleştiriliyor"
    for f in README.md README.tr.md; do
      [ -f "$f" ] || continue
      sed -i \
        -e "s|<your-username>|${GH_USER}|g" \
        -e "s|<kullanici-adin>|${GH_USER}|g" \
        -e "s|(README\.tr\.md)|(${WEB_URL}/blob/main/README.tr.md)|g" \
        "$f"
    done
  fi
 
  # ------------------------------------------------------------ 2) pyproject urls
  if ! grep -q '^\[project\.urls\]' pyproject.toml; then
    info "pyproject.toml içine [project.urls] ekleniyor"
    cat >> pyproject.toml <<EOF
 
[project.urls]
Homepage = "${WEB_URL}"
Issues = "${WEB_URL}/issues"
EOF
  fi
fi
 
# ---------------------------------------------------------------- 3) init
if [ ! -d .git ]; then
  info "git deposu oluşturuluyor"
  git init -q -b main 2>/dev/null || { git init -q; git symbolic-ref HEAD refs/heads/main; }
else
  info "git deposu zaten var, atlanıyor"
fi
 
# ---------------------------------------------------------------- 4) git kimliği + commit
# (Kimlik, depo oluşturulduktan sonra yazılır; yoksa 'git config' hata verir.)
if ! git config user.name >/dev/null 2>&1; then
  read -r -p "git için adın (commit'lerde görünür): " n || true
  [ -n "${n:-}" ] && git config user.name "$n"
fi
if ! git config user.email >/dev/null 2>&1; then
  warn "E-posta GitHub'daki commit'lerinde herkese görünür. Gizlemek için GitHub'ın"
  warn "'...@users.noreply.github.com' adresini kullanabilirsin (Settings -> Emails)."
  read -r -p "git için e-posta: " m || true
  [ -n "${m:-}" ] && git config user.email "$m"
fi
git config user.name  >/dev/null 2>&1 || die "git user.name ayarlı değil"
git config user.email >/dev/null 2>&1 || die "git user.email ayarlı değil"
 
# Gizli bilgi sızdırma kazalarına karşı basit kontrol
if git ls-files --others --exclude-standard | grep -Eqi '(\.pypirc|\.env|id_rsa|id_ed25519|token)'; then
  warn "Commit edilecek dosyalar arasında hassas görünen bir şey var:"
  git ls-files --others --exclude-standard | grep -Ei '(\.pypirc|\.env|id_rsa|id_ed25519|token)' >&2 || true
  ask_yes "Yine de devam edilsin mi?" || die "İptal edildi."
fi
 
git add -A
if git diff --cached --quiet; then
  info "Commit edilecek yeni değişiklik yok"
else
  info "Commit atılıyor"
  git commit -q -m "$COMMIT_MSG"
fi
git rev-parse --verify HEAD >/dev/null 2>&1 || die "Hiç commit yok; commit edilecek dosya bulunamadı."
git branch -M main
 
# ---------------------------------------------------------------- 5) remote + push
HAVE_GH=0
if [ "$CUSTOM_REMOTE" = 0 ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  HAVE_GH=1
fi
 
if git remote get-url origin >/dev/null 2>&1; then
  CUR="$(git remote get-url origin)"
  if [ "$CUR" != "$REMOTE_URL" ]; then
    warn "origin zaten başka bir adrese bağlı: $CUR"
    if ask_yes "origin '$REMOTE_URL' olarak değiştirilsin mi?"; then
      git remote set-url origin "$REMOTE_URL"
    fi
  fi
elif [ "$HAVE_GH" = 1 ] && [[ "$REMOTE_URL" == *github.com* ]]; then
  VIS="--public"; [ "$PRIVATE" = 1 ] && VIS="--private"
  if ask_yes "GitHub'da '${GH_USER}/${REPO_NAME}' ($VIS) oluşturulsun mu?"; then
    info "gh ile depo oluşturuluyor"
    gh repo create "${GH_USER}/${REPO_NAME}" "$VIS" --source=. --remote=origin
  fi
fi
 
if ! git remote get-url origin >/dev/null 2>&1; then
  if [[ "$REMOTE_URL" == *github.com* ]]; then
    printf '\n%sGitHub deposu henüz yok gibi görünüyor.%s Önce şunu yap:\n' "$B" "$N"
    printf '  1. https://github.com/new adresine git\n'
    printf '  2. Repository name: %s\n' "$REPO_NAME"
    printf '  3. "Add a README", ".gitignore" ve "license" seçeneklerini İŞARETLEME (projede hazır)\n'
    printf '  4. "Create repository" de\n\n'
    ask_yes "Depoyu oluşturdun mu? Devam edilsin mi?" || { warn "Durduruldu. Hazır olunca betiği tekrar çalıştır."; exit 0; }
  fi
  git remote add origin "$REMOTE_URL"
fi
 
info "GitHub'a gönderiliyor (git push)"
if ! git push -u origin main; then
  cat >&2 <<EOF
 
push başarısız oldu. Sık nedenler:
  - Depo GitHub'da henüz oluşturulmamış ya da adı farklı: ${WEB_URL}
  - HTTPS kullanıyorsan şifre yerine kişisel erişim tokenı (PAT) gerekir:
      https://github.com/settings/tokens
    ya da daha kolayı: 'gh auth login' (GitHub CLI) / SSH anahtarı + './setup_git.sh -s'
  - Uzak depoda zaten commit'ler var (README ile oluşturduysan):
      git pull --rebase origin main && git push -u origin main
EOF
  exit 1
fi
 
info "Tamam! Depon: ${WEB_URL}"
printf '\nSıradaki adım (PyPI için): python -m build && twine check dist/*  (bkz. RELEASING.md)\n'
