#!/usr/bin/env python3
"""日本語化の漏れと崩れを確かめる。

確認する内容:
  1. config/locales/arinko_ja.yml が読め、上流 i18n.yml の ja と深くマージした ja が
     en の全キーを持つ（足りないキーの一覧が空）。arinko_ja.yml と上流 ja でキーが重ならない。
  2. キーごとに、en と ja の埋め込み変数 %{...} の集合が同じ。HTML タグの並びも同じ。
  3. app/javascript/template_builder/i18n_ja.js のキー集合が i18n.js の en と一致し、
     各キーの {変数} の集合も同じ。

使い方: python3 tools/arinko/check_ja_locale.py [--list-english]
  --list-english: ja の値が en と同じ（訳し忘れの疑い）のキーも一覧に出す。
終了コード: 問題がなければ 0、あれば 1。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
UPSTREAM_YML = os.path.join(ROOT, 'config/locales/i18n.yml')
ARINKO_YML = os.path.join(ROOT, 'config/locales/arinko_ja.yml')
BUILDER_DIR = os.path.join(ROOT, 'app/javascript/template_builder')

RAILS_VAR = re.compile(r'%\{[^}]*\}|(?<!%)\{[^{}]*\}')  # %{name} と、メール本文などの {template.name}
JS_VAR = re.compile(r'\{[^{}]*\}')
TAG = re.compile(r'</?[a-zA-Z][^>]*>')
# 言語名（language_*）と、翻訳しない固有名詞・略語は同じ値でよい
SAME_OK = re.compile(r'^(language_.*|kba.*|pro|api|hmac|mcp|sms|kba|ssn|ein|iban|url|zip|ok)$', re.I)


def flatten(node, path=()):
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(flatten(v, path + (str(k),)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(flatten(v, path + (str(i),)))
    else:
        out['.'.join(path)] = node
    return out


def multiset(pattern, text):
    return sorted(pattern.findall(text if isinstance(text, str) else str(text)))


def tags_normalized(text):
    # 属性（class・href など）は訳さないので、タグ名と開閉だけを比べる
    return sorted(re.sub(r'^(</?[a-zA-Z0-9]+).*?(/?)>$', r'\1\2>', t) for t in TAG.findall(str(text)))


def check_yaml(list_english):
    problems = []
    upstream = yaml.safe_load(open(UPSTREAM_YML, encoding='utf-8'))
    en = flatten(upstream['en'])
    up_ja = flatten(upstream['ja'])
    try:
        arinko = yaml.safe_load(open(ARINKO_YML, encoding='utf-8'))
    except Exception as e:  # noqa: BLE001
        print(f'[1] NG arinko_ja.yml を読めません: {e}')
        return False
    ar_ja = flatten(arinko['ja'])
    ja = dict(up_ja)
    overlap = sorted(set(ar_ja) & set(up_ja))
    ja.update(ar_ja)

    missing = sorted(set(en) - set(ja))
    extra = sorted(set(ar_ja) - set(en))
    print(f'[1] en のキー {len(en)} 件 / 上流 ja {len(up_ja)} 件 / arinko_ja {len(ar_ja)} 件')
    print(f'[1] 足りないキー {len(missing)} 件 / 上流と重なるキー {len(overlap)} 件 / en に無いキー {len(extra)} 件')
    for k in missing:
        print('    足りない:', k)
        problems.append(k)
    for k in overlap:
        print('    上流と重複:', k)
        problems.append(k)
    for k in extra:
        print('    en に無い:', k)
        problems.append(k)

    bad_vars = []
    bad_tags = []
    for k, v in en.items():
        if k not in ja:
            continue
        if multiset(RAILS_VAR, v) != multiset(RAILS_VAR, ja[k]):
            bad_vars.append(k)
        if tags_normalized(v) != tags_normalized(ja[k]):
            bad_tags.append(k)
    print(f'[2] %{{...}} が en と一致しないキー {len(bad_vars)} 件 / HTML タグが en と一致しないキー {len(bad_tags)} 件')
    for k in bad_vars:
        print('    変数が違う:', k, '| en:', en[k], '| ja:', ja[k])
    for k in bad_tags:
        print('    タグが違う:', k, '| en:', en[k], '| ja:', ja[k])
    problems += bad_vars + bad_tags

    same = sorted(k for k in ar_ja if k in en and ar_ja[k] == en[k] and not SAME_OK.match(k.split('.')[-1])
                  and re.search(r'[A-Za-z]{3,}', str(en[k])))
    print(f'[参考] ja の値が en と同じで、訳し忘れの疑いがあるキー {len(same)} 件')
    if list_english:
        for k in same:
            print('    同一:', k, '|', en[k])
    return not problems


def js_data():
    """i18n.js の en と i18n_ja.js の ja を {キー: 値} で返す。node があれば import、なければ正規表現。"""
    node = shutil.which('node')
    if node:
        with tempfile.TemporaryDirectory() as tmp:
            src = open(os.path.join(BUILDER_DIR, 'i18n.js'), encoding='utf-8').read()
            src = src.replace("'./i18n_ja'", "'./i18n_ja.mjs'")
            open(os.path.join(tmp, 'i18n.mjs'), 'w', encoding='utf-8').write(src)
            shutil.copy(os.path.join(BUILDER_DIR, 'i18n_ja.js'), os.path.join(tmp, 'i18n_ja.mjs'))
            open(os.path.join(tmp, 'run.mjs'), 'w', encoding='utf-8').write(
                "import * as i from './i18n.mjs'\nconsole.log(JSON.stringify({en: i.en, ja: i.ja}))\n")
            r = subprocess.run([node, os.path.join(tmp, 'run.mjs')], capture_output=True, text=True, cwd=tmp)
            if r.returncode == 0:
                d = json.loads(r.stdout)
                return d['en'], d['ja'], 'node'
            print('    node の import に失敗したため正規表現で比べます:', r.stderr.strip()[:200])
    key_re = re.compile(r"^  ([A-Za-z0-9_]+): '((?:[^'\\]|\\.)*)'", re.M)

    def parse(text):
        return {m.group(1): m.group(2).replace("\\'", "'") for m in key_re.finditer(text)}
    i18n = open(os.path.join(BUILDER_DIR, 'i18n.js'), encoding='utf-8').read()
    en_text = i18n[:i18n.index('\nconst es = {')]
    ja_text = open(os.path.join(BUILDER_DIR, 'i18n_ja.js'), encoding='utf-8').read()
    return parse(en_text), parse(ja_text), 'regexp'


def check_js():
    en, ja, how = js_data()
    missing = sorted(set(en) - set(ja))
    extra = sorted(set(ja) - set(en))
    bad = sorted(k for k in en if k in ja and multiset(JS_VAR, en[k]) != multiset(JS_VAR, ja[k]))
    print(f'[3] template_builder（{how}）: en {len(en)} 件 / ja {len(ja)} 件 / 足りない {len(missing)} 件 / 余分 {len(extra)} 件 / {{変数}}不一致 {len(bad)} 件')
    for k in missing:
        print('    足りない:', k)
    for k in extra:
        print('    余分:', k)
    for k in bad:
        print('    変数が違う:', k, '| en:', en[k], '| ja:', ja[k])
    return not (missing or extra or bad)


def main():
    list_english = '--list-english' in sys.argv
    ok1 = check_yaml(list_english)
    ok2 = check_js()
    print('結果:', 'OK' if ok1 and ok2 else 'NG')
    return 0 if ok1 and ok2 else 1


if __name__ == '__main__':
    sys.exit(main())
