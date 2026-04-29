"""
正規表現 docs --> https://docs.python.org/ja/3/library/re.html
"""
import re 
import os
import glob
import dill
import argparse
import pathlib
import chardet
baseDir = pathlib.Path(__file__).parent.resolve()

TXT_DIR = str(baseDir / "txt_converted")
SPAN_BF = 60
CONTEXT_LEN = 130
FORCES_READ_FILE = True
FILE_PATHS = []
ALL_FILE_STR_LIST = []
ALL_FILE_STR_LIST_L = []

RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
BLUE = '\033[34m'
BOLD = '\033[1m'
END = '\033[0m'

def main():

    ## get argument
    parser = argparse.ArgumentParser()
    parser.add_argument("search_string", help="search string", type=str)
    parser.add_argument("-a","--additional_search_string", help="additional search string", type=str)
    args = parser.parse_args()
   
    ## load txt data
    load_txt_data()
    
    ## seach
    res = search(args.search_string,  None if args.additional_search_string is None else args.additional_search_string,
                 excluding=None)
    for c in res:
        # disp_cxt =  add_stress_tag(c['context'], c['rel_pos_found'][0], c['rel_pos_found'][1], RED, END)
        # for rps in c['rel_pos_sub']:
        #     disp_cxt =  add_stress_tag(disp_cxt, rps[0], rps[1], BLUE, END)
        
        tmp = []
        for rps in c['rel_pos_sub_lst']:
            tmp.append({'pos': rps, 'tag':[BLUE, END]})
        disp_cxt = add_stress_tag2(c['context'], pos_main={'pos': c['rel_pos_found'], 'tag':[RED, END]}, pos_sub_lst=tmp)

        print(f"{c['pos_found'][0]:>8.0f}  ", disp_cxt, "  "+os.path.basename(c['file'])[0:20])
    
    print(f"--- FOUND LINES: {len(res)} ---")


def add_stress_tag2(txt, pos_main:dict, pos_sub_lst:list=None):
    """
    txtの指定位置に指定したタグを挟み込む処理を行う。
    pos_main および pos_sub_lstの各要素 の形式は以下の通り
    {
        "pos":[強調開始位置(int), 終了位置(int)], 
        "tag":[強調用開始タグ(str),終了タグ(str)]
    }
    """
    # タグ挿入インデックスのリスト
    pos = [pos_main['pos'][0], pos_main['pos'][1]]
    # 上記に対する挿入タグのリスト
    tag = [pos_main['tag'][0], pos_main['tag'][1]]

    # subがあればそれも追加
    if pos_sub_lst is not None:
        for ps in pos_sub_lst:
            pos.append(ps['pos'][0])
            pos.append(ps['pos'][1])
            tag.append(ps['tag'][0])
            tag.append(ps['tag'][1])
    
    # まとめてソートする
    # zip to sort
    zipped = zip(pos, tag)
    # posを基準に照準でソート
    zipped_sorted = sorted(zipped)

    # txtにタグを順番に挟み込む
    ret = ""
    p_bf = 0
    for p, t in zipped_sorted:
        ret += txt[p_bf:p] + t
        p_bf = p
    else:
        ret += txt[p_bf:]
    
    return ret


    
def load_txt_data():
    
    global ALL_FILE_STR_LIST
    global ALL_FILE_STR_LIST_L
    global FILE_PATHS
    
    ## LOAD TXT DATA ##
    pickled = os.path.join(baseDir, "all_txt_pickled")
    pickled_l = os.path.join(baseDir, "all_txt_pickled_l")
    pickled_fn = os.path.join(baseDir, "all_txt_pickled_fn")

    if FORCES_READ_FILE or (not os.path.isfile(pickled)):
        # load from file
        FILE_PATHS = glob.glob(os.path.join(TXT_DIR, "*.txt"))
        for file in FILE_PATHS:
            # f = open(file, "r", encoding=get_file_encoding(file)) # これはおそい
            f = open(file, "r") 
            try:
                txt = f.read()
            except:
                print(f"FAILED TO READ {file}")
                continue
            # f.close()
            txt_nm = normalize_pdf_text(txt)
            ALL_FILE_STR_LIST.append(txt_nm)
            ALL_FILE_STR_LIST_L.append(txt_nm.lower())
        # serialize and save
        if not FORCES_READ_FILE:
            with open(pickled, 'wb') as f:
                dill.dump(ALL_FILE_STR_LIST, f)         
            with open(pickled_l, 'wb') as f:
                dill.dump(ALL_FILE_STR_LIST_L, f)         
            with open(pickled_fn, 'wb') as f:
                dill.dump(FILE_PATHS, f)         
    else:
        # load from pickled one
        with open(pickled, 'rb') as f:
            ALL_FILE_STR_LIST = dill.load(f)  
        with open(pickled_l, 'rb') as f:
            ALL_FILE_STR_LIST_L = dill.load(f)  
        with open(pickled_fn, 'rb') as f:
            FILE_PATHS = dill.load(f)  
        print("pickled list loaded") 


def normalize_pdf_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 単語途中のハイフネーションを復元
    text = re.sub(r'([A-Za-z])-\n([A-Za-z])', r'\1\2', text)

    # 残りの単独改行を空白へ
    # text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)

    # 連続空白を整理
    text = re.sub(r'[ \t]+', ' ', text)

    # 段落区切りは残したいならここは調整
    # text = re.sub(r'\n{2,}', '\n\n', text)

    return text.strip()


def search(target_wd, context1_wd=None, context2_wd=None, excluding=None,
           range: list = None, is_case_sensitive: bool = True):
    """
    改訂方針（高速化）:
      - 文脈込みの巨大正規表現 ".{bf} ... .{af}" を廃止
      - まず検索語（ユーザー正規表現）だけを finditer してヒット位置を取得
      - 文脈文字列は Python スライスで切り出す（ctx_start/ctx_end）
      - excluding / context1 / context2 は文脈スライスに対してのみ検索
      - 単語境界は原則付与（\b(?:PAT)\b）
        ※PATが空白を含む場合は、空白を「空白 or ハイフン群」に拡張（任意）
    """
    ret = []
    if target_wd is None or len(target_wd.strip()) == 0:
        return ret

    # 文脈長（前後）: スライスで切るので len(target_wd) を引かない
    if range is None:
        ctx_len_bf, ctx_len_af = SPAN_BF, CONTEXT_LEN - SPAN_BF
    else:
        ctx_len_bf, ctx_len_af = range
    
    flags = 0 if is_case_sensitive else re.IGNORECASE

    # ハイフンと空白を同等の区切りとして扱いたい場合の区切りクラス
    # （PDF由来で別ハイフンが混ざるなら必要に応じて追加）
    SEP = r"(?:[\s\u2010-\u2015\u2212-]+)"  # whitespace + various hyphens
    
    def compile_query(user_pat: str) -> re.Pattern | None:
        """
        ユーザーの正規表現をコンパイルする。
        - デフォルトで単語境界を付ける: \b(?:PAT)\b
        - ただし user_pat に空白が含まれる場合は、その空白を SEP に拡張して熟語検索を容易にする
          例: "in law" -> r"\b(?:in(?:[\s-]+)law)\b"
        """
        if user_pat is None:
            return None
        p = user_pat.strip()
        if len(p) == 0:
            return None

        # 熟語入力（空白を含む）なら、空白を SEP に置換して「空白/ハイフン揺れ」を許容
        # ※in-law を in law にヒットさせる必要はないと言っていましたが、
        #   「空白とハイフンを同じ扱いにしたい」という要件に沿うため、ここでは許容します。
        #   不要なら次の2行（re.sub）を削除してください。
        # if re.search(r"\s", p):
        #     p = re.sub(r"\s+", lambda m: SEP, p)

        print("PATTERN =", repr(p), "WRAPPED =", repr(rf"\b(?:{p})\b"))

        # 単語境界で囲う（要求仕様）
        return re.compile(rf"\b(?:{p})\b", flags)
        # return re.compile(rf"(?<!\w)(?:{p})(?!\w)", flags) #\bのほうが高速
    
    pat_main = compile_query(target_wd)
    if pat_main is None:
        return ret

    pat_exc = compile_query(excluding) if excluding is not None and len(excluding.strip()) > 0 else None
    pat_ctx1 = compile_query(context1_wd) if context1_wd is not None and len(context1_wd.strip()) > 0 else None
    pat_ctx2 = compile_query(context2_wd) if context2_wd is not None and len(context2_wd.strip()) > 0 else None

    for i, (file_txt_org, file_txt_lw, file) in enumerate(zip(ALL_FILE_STR_LIST, ALL_FILE_STR_LIST_L, FILE_PATHS)):

        # テキスト本体：IGNORECASE を使うので lower 版を使う必要は基本ない
        file_txt = file_txt_org
                              
        for m in pat_main.finditer(file_txt):

            # 文脈スライス（regexに作らせない）
            ctx_start = max(0, m.start() - ctx_len_bf)
            ctx_end = min(len(file_txt), m.end() + ctx_len_af)

            ctx_txt_org = file_txt_org[ctx_start:ctx_end]  # 表示用（オリジナル）
            ctx_txt = ctx_txt_org  # 検索用も同じでOK（IGNORECASEで制御）

            # 除外語チェック（文脈内のみ）
            if pat_exc is not None and pat_exc.search(ctx_txt):
                continue

            # 文脈語1のサーチ（文脈内のみ）
            rel_pos_sub_lst = []
            if pat_ctx1 is not None:
                for f in pat_ctx1.finditer(ctx_txt):
                    rel_pos_sub_lst.append([f.start(), f.end()])
                if len(rel_pos_sub_lst) == 0:
                    continue

            # 文脈語2のサーチ（文脈内のみ）
            rel_pos_sub_lst2 = []
            if pat_ctx2 is not None:
                for f in pat_ctx2.finditer(ctx_txt):
                    rel_pos_sub_lst2.append([f.start(), f.end()])
                if len(rel_pos_sub_lst2) == 0:
                    continue
            
            # 検索語の相対位置は m から算出（追加の re.search は不要）
            rel_start = m.start() - ctx_start
            rel_end = m.end() - ctx_start


            ret.append({
                "file": file,                 # テキストファイルパス
                "file_id": i,                 # ファイルのid
                "file_txt": file_txt_org,     # テキスト全文（表示用）
                "pos_found": [ctx_start, ctx_end],      # 文脈スライスの範囲
                "context": ctx_txt_org,                 # 文脈文字列
                "rel_pos_found": [rel_start, rel_end],  # context内でのヒット位置
                "rel_pos_sub_lst": rel_pos_sub_lst,
                "rel_pos_sub_lst2": rel_pos_sub_lst2
            })
    
    return ret


def get_file_encoding(filepath):
    with open(filepath, 'rb') as f:
        c = f.read()
        result = chardet.detect(c)
    return result['encoding']


# *を\w*に変換するメソッド。もとから\w*のものはそのままで変換しない
filter = lambda x: re.sub(r"\*", r"\\w*", x) if re.search(r"([a-z]\*|^\*)", x) and not re.search(r"(\\[a-z]\*)", x) else x

# *を[^ ]*に変換するメソッド。もとから\w*のものはそのままで変換しない。頭に*が入ってきても適切に対応
def filter2(x):
    # 頭に"*"が含まれるかどうか判定
    if re.search(r"^\*", x):
        # (含まれる)
        # 頭の*を置換
        x = re.sub("^\*", "[^ ]*", x)
        # 残りを置換
        if re.search(r"([a-z0-9]\*|^\*)", x[5:]) and not re.search(r"(\\[a-z0-9]\*)", x[5:]):
            # x = x[0:5] + re.sub(r"\*", r"\\w*", x[5:])
            x = x[0:5] + re.sub(r"\*", "[^ ]*", x[5:])
    else:
        # (含まれない)
        # 頭以外をまとめて置換
        if re.search(r"([a-z0-9]\*|^\*)", x) and not re.search(r"(\\[a-z0-9]\*)", x):
            # x = re.sub(r"\*", r"\\w*", x)
            x = re.sub(r"\*", "[^ ]*", x)
    return x

if __name__ == "__main__":
    main()
    # filter2("flow\w*")