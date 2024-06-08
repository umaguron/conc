import re 
import os
import glob
import dill
import argparse
import pathlib
baseDir = pathlib.Path(__file__).parent.resolve()

TXT_DIR = os.path.join(baseDir, "txt")
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
                 excluding="do not")
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
            f = open(file, "r", encoding="UTF-16")
            try:
                txt = f.read()
            except:
                print(f"FAILED TO READ {file}")
                continue
            # f.close()
            ALL_FILE_STR_LIST.append(txt)
            ALL_FILE_STR_LIST_L.append(txt.lower())
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

def search(target_wd, context1_wd=None, context2_wd=None, excluding=None, range:list=None):
    ret = []
    if len(target_wd.strip())==0:
        return ret
    
    if range is None:
        ctx_len_bf, ctx_len_af = SPAN_BF, CONTEXT_LEN-SPAN_BF-len(target_wd)
    else:
        ctx_len_bf, ctx_len_af = range

    prog = re.compile(".{" + f"{ctx_len_bf}" + r"}\s" \
                            + target_wd.lower() \
                            + r"\s.{" + f"{ctx_len_af}" + "}")
    
    for i, (file_txt, file_txt_lw, file) in enumerate(zip(ALL_FILE_STR_LIST, ALL_FILE_STR_LIST_L, FILE_PATHS)):

        contexts = prog.finditer(file_txt_lw)
                              
        for ctx in contexts: 
            # roop for each found result

            # 除外語を含むかチェック
            if excluding is not None:
                if re.search(r"\s" + excluding.lower() + r"\s", file_txt_lw[ ctx.start() : ctx.end() ]):
                    continue
                
            rel_pos_sub_lst = []
            if context1_wd is not None:
                # 文脈語のサーチ (前後の空白も含めてサーチ)
                founds = re.finditer(r"\s" + context1_wd.lower() + r"\s", file_txt_lw[ ctx.start() : ctx.end() ])
                for f in founds:
                    rel_pos_sub_lst.append([f.start()+1, f.end()-1]) # 空白分を除く

                if len(rel_pos_sub_lst)==0: continue
            
            rel_pos_sub_lst2 = []
            if context2_wd is not None:
                # 文脈語2のサーチ (前後の空白も含めてサーチ)
                founds = re.finditer(r"\s" + context2_wd.lower() + r"\s", file_txt_lw[ ctx.start() : ctx.end() ])
                for f in founds:
                    rel_pos_sub_lst2.append([f.start()+1, f.end()-1]) # 空白分を除く

                if len(rel_pos_sub_lst2)==0: continue
            
            """
            検索語の正確な文字数が知りたいので、上の処理で
            マッチした文字列 (ctx.group())についてさらに、今度はtarget_wd単独で検索する。
            検索範囲を[ctx_len_bf+1:]としたのは、万が一検索語が前のctx_len_bf文字以内にも出現している場合を想定している
            """
            mtc = re.search(target_wd.lower(), ctx.group()[ctx_len_bf+1:])

            ret.append({
                "file": file, # テキストファイルパス
                "file_id": i, # ファイルのid
                "file_txt": file_txt, # テキスト全文
                "pos_found": [ctx.start(), ctx.end()], # 検索された語を中心に前後も含めた文字列のインデックス範囲　（長さは引数rangeで定義される）
                "context": file_txt[ ctx.start() : ctx.end()], # 検索された語を中心に前後も含めた文字列そのもの （長さは引数rangeで定義される）
                "rel_pos_found": [ctx_len_bf+1, ctx_len_bf+1+len(mtc.group())], # 文字列"context"の中では何文字目から何文字目までに検索語があるか
                "rel_pos_sub_lst": rel_pos_sub_lst, # 文字列"context" を対象に文脈後を検索した結果。何文字目から何文字目までに文脈語があるか。複数マッチの可能性があるのでリストにしている。
                "rel_pos_sub_lst2": rel_pos_sub_lst2 # 文字列"context" を対象に文脈後を検索した結果。何文字目から何文字目までに文脈語があるか。複数マッチの可能性があるのでリストにしている。
            })
    
    return ret

if __name__ == "__main__":
    main()