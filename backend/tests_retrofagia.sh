#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"

# ===== util =====
need() { command -v "$1" >/dev/null || { echo "❌ faltando dependência: $1"; exit 1; }; }
need curl
need jq

pass() { echo -e "✅ $*"; }
fail() { echo -e "❌ $*"; exit 1; }

# curl helpers
post_json() { # path json [token]
  local path="$1" json="$2" token="${3:-}"
  local hdr=(-H 'Content-Type: application/json' -H 'Accept: application/json')
  [[ -n "$token" ]] && hdr+=(-H "Authorization: Bearer $token")
  curl -sS --fail-with-body "${hdr[@]}" -X POST "$API_URL$path" -d "$json"
}
post_nobody_204() { # path [token] => expect 204
  local path="$1" token="${2:-}"
  local hdr=(-H 'Accept: application/json')
  [[ -n "$token" ]] && hdr+=(-H "Authorization: Bearer $token")
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" "${hdr[@]}" -X POST "$API_URL$path")
  [[ "$code" == "204" ]] || fail "POST $path esperava 204, recebeu $code"
}
get_json() { # path [token]
  local path="$1" token="${2:-}"
  local hdr=(-H 'Accept: application/json')
  [[ -n "$token" ]] && hdr+=(-H "Authorization: Bearer $token")
  curl -sS --fail-with-body "${hdr[@]}" "$API_URL$path"
}
patch_json() { # path json [token]
  local path="$1" json="$2" token="${3:-}"
  local hdr=(-H 'Content-Type: application/json' -H 'Accept: application/json')
  [[ -n "$token" ]] && hdr+=(-H "Authorization: Bearer $token")
  curl -sS --fail-with-body "${hdr[@]}" -X PATCH "$API_URL$path" -d "$json"
}
delete_204() { # path [token]
  local path="$1" token="${2:-}"
  local hdr=(-H 'Accept: application/json')
  [[ -n "$token" ]] && hdr+=(-H "Authorization: Bearer $token")
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" "${hdr[@]}" -X DELETE "$API_URL$path")
  [[ "$code" == "204" ]] || fail "DELETE $path esperava 204, recebeu $code"
}

register_or_login() { # user email pass -> token
  local u="$1" e="$2" p="$3" tok=""
  set +e
  tok=$(post_json "/auth/register" "{\"username\":\"$u\",\"email\":\"$e\",\"password\":\"$p\"}" | jq -r .access_token 2>/dev/null)
  if [[ -z "$tok" || "$tok" == "null" ]]; then
    tok=$(post_json "/auth/login" "{\"username_or_email\":\"$u\",\"password\":\"$p\"}" | jq -r .access_token)
  fi
  set -e
  [[ -n "$tok" && "$tok" != "null" ]] || fail "não consegui obter token para $u"
  echo "$tok"
}

line() { echo "------------------------------------------------------------"; }

echo "🔎 Testando Retrofagia em $API_URL"
line

# 0) Health
root=$(get_json "/")
echo "$root" | jq -e '.status == "ok"' >/dev/null || fail "/ root não respondeu ok"
pass "/ -> ok"

# 1) Usuários A e B
USER_A="jorge"
USER_B="maria"
PASSWD="123456"
TOKEN_A=$(register_or_login "$USER_A" "$USER_A@example.com" "$PASSWD")
TOKEN_B=$(register_or_login "$USER_B" "$USER_B@example.com" "$PASSWD")
pass "auth -> tokens obtidos p/ $USER_A e $USER_B"

ME_A_JSON=$(get_json "/auth/me" "$TOKEN_A")
ME_B_JSON=$(get_json "/auth/me" "$TOKEN_B")
USER_A_ID=$(echo "$ME_A_JSON" | jq -r .id)
USER_B_ID=$(echo "$ME_B_JSON" | jq -r .id)
pass "/auth/me -> ids: A=$USER_A_ID, B=$USER_B_ID"

# 2) Criar disco único, buscar e capturar id
TS=$(date +%s)
MCODE="AUTO-$TS"
REC_JSON=$(post_json "/records" "{\"matrix_code\":\"$MCODE\",\"title\":\"LP Test $TS\",\"artist\":\"Tester\",\"year\":1977,\"genre\":\"Rock\",\"label\":\"Retro\"}" "$TOKEN_A")
echo "$REC_JSON" | jq -e '.id and .matrix_code' >/dev/null || fail "POST /records não retornou JSON esperado"
RID=$(echo "$REC_JSON" | jq -r .id)
pass "POST /records -> id=$RID (matrix_code=$MCODE)"

SRCH=$(get_json "/records?code=$MCODE" "$TOKEN_A")
test_rid=$(echo "$SRCH" | jq -r '.[0].id')
[[ "$test_rid" == "$RID" ]] || fail "GET /records?code não achou o disco criado"
pass "GET /records?code -> ok"

# 3) Coleção, review, feed do A
col=$(post_json "/collection/$RID" "{}" "$TOKEN_A")
echo "$col" | jq -e '.status=="ok"' >/dev/null || fail "POST /collection falhou"
pass "POST /collection/{id} -> ok"

rev=$(post_json "/reviews" "{\"record_id\":\"$RID\",\"rating\":9,\"comment\":\"Teste de review $TS\"}" "$TOKEN_A")
echo "$rev" | jq -e '.id and .rating==9' >/dev/null || fail "POST /reviews falhou"
pass "POST /reviews -> ok"

feedA=$(get_json "/feed?limit=10" "$TOKEN_A")
echo "$feedA" | jq -e 'type=="array" and length>0' >/dev/null || fail "GET /feed (A) vazio/inesperado"
echo "$feedA" | jq -e 'map(.verb) | index("ADD_RECORD") != null' >/dev/null || fail "feed A sem ADD_RECORD"
echo "$feedA" | jq -e 'map(.verb) | index("REVIEW") != null' >/dev/null || fail "feed A sem REVIEW"
pass "GET /feed (A) contém ADD_RECORD e REVIEW"

# 4) Comentário no disco -> feed COMMENT
cmt=$(post_json "/records/$RID/comments" "{\"content\":\"Comentário no disco $TS\"}" "$TOKEN_A")
echo "$cmt" | jq -e '.id and .content' >/dev/null || fail "POST /records/{id}/comments falhou"
feedA2=$(get_json "/feed?limit=10" "$TOKEN_A")
echo "$feedA2" | jq -e 'map(.verb) | index("COMMENT") != null' >/dev/null || fail "feed A sem COMMENT"
pass "POST /records/{id}/comments -> feed COMMENT ok"

# 5) Favoritar e listar favoritos
fav=$(patch_json "/collection/$RID" '{"is_favorite":true}' "$TOKEN_A")
echo "$fav" | jq -e '.is_favorite==true' >/dev/null || fail "PATCH /collection/{id} is_favorite falhou"
favs=$(get_json "/collection/me/favorites" "$TOKEN_A")
echo "$favs" | jq -e --arg rid "$RID" 'map(.id)==null or (map(.id) | index($rid) != null)' >/dev/null || fail "GET /collection/me/favorites não contém o record favorito"
pass "favoritos -> ok"

# 6) Busca avançada (year/genre/label)
adv=$(get_json "/records?year=1977&genre=rock&label=retro" "$TOKEN_A")
echo "$adv" | jq -e 'type=="array"' >/dev/null || fail "busca avançada não retornou array"
pass "busca avançada -> ok"

# 7) Seguir: B segue A, feed do B deve ver atividades do A
post_nobody_204 "/users/$USER_A_ID/follow" "$TOKEN_B"
pass "POST /users/{A}/follow (B -> A) -> 204 ok"

feedB=$(get_json "/feed?limit=10" "$TOKEN_B")
echo "$feedB" | jq -e 'type=="array"' >/dev/null || fail "GET /feed (B) falhou"
# não garantimos ordem exata, mas B deve ver ADD_RECORD/REVIEW/COMMENT do A em algum momento
echo "$feedB" | jq -e 'map(.verb) | (index("ADD_RECORD")!=null or index("REVIEW")!=null or index("COMMENT")!=null)' >/dev/null || fail "feed B não mostra atividades do A"
pass "feed (B) mostra atividades do A"

# 8) Like + comentar activity
AID=$(echo "$feedA2" | jq -r '.[0].id')
# like 204
post_nobody_204 "/feed/$AID/like" "$TOKEN_A"
# comentar activity
acmt=$(post_json "/feed/$AID/comments" "{\"content\":\"🔥 test $TS\"}" "$TOKEN_A")
echo "$acmt" | jq -e '.id and .content' >/dev/null || fail "POST /feed/{id}/comments falhou"
acmt_list=$(get_json "/feed/$AID/comments" "$TOKEN_A")
echo "$acmt_list" | jq -e 'type=="array" and length>0' >/dev/null || fail "GET /feed/{id}/comments vazio"
pass "like + comentários em activity -> ok"

# 9) Sanity final: tentar criar matrix_code duplicado (espera 400)
set +e
dup=$(post_json "/records" "{\"matrix_code\":\"$MCODE\",\"title\":\"dup\",\"artist\":\"dup\"}" "$TOKEN_A" 2>&1)
code=$?
set -e
if [[ $code -ne 0 ]]; then
  echo "$dup" | grep -q "matrix_code já existe" && pass "validação de duplicidade -> ok" || fail "erro inesperado no teste de duplicidade"
else
  fail "esperava 400 na duplicidade de matrix_code, mas deu sucesso"
fi

# 10) Mensagens privadas (DM) entre usuários
# Criar conversa A <-> B
CID=$(post_json "/conversations" "{\"other_user_id\":\"$USER_B_ID\"}" "$TOKEN_A" | jq -r .id)
[[ -n "$CID" && "$CID" != "null" ]] || fail "POST /conversations não retornou id"

# Enviar mensagem de A para B
msg1=$(post_json "/conversations/$CID/messages" "{\"content\":\"Oi Maria! Teste $TS\"}" "$TOKEN_A")
echo "$msg1" | jq -e '.id and .content' >/dev/null || fail "POST /conversations/{id}/messages falhou"
pass "A -> B: mensagem enviada"

# Enviar mensagem de B para A
msg2=$(post_json "/conversations/$CID/messages" "{\"content\":\"Oi Jorge! Recebido $TS\"}" "$TOKEN_B")
echo "$msg2" | jq -e '.id and .content' >/dev/null || fail "POST /conversations/{id}/messages (B) falhou"
pass "B -> A: mensagem enviada"

# Listar histórico de mensagens (A)
msgsA=$(get_json "/conversations/$CID/messages" "$TOKEN_A")
echo "$msgsA" | jq -e 'type=="array" and length>=2' >/dev/null || fail "GET /conversations/{id}/messages (A) vazio"
pass "A vê histórico de conversa"

# Listar histórico de mensagens (B)
msgsB=$(get_json "/conversations/$CID/messages" "$TOKEN_B")
echo "$msgsB" | jq -e 'type=="array" and length>=2' >/dev/null || fail "GET /conversations/{id}/messages (B) vazio"
pass "B vê histórico de conversa"

line
echo "🎉 TODOS OS TESTES PASSARAM!"
