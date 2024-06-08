import os
import sys
import pathlib
import time
baseDir = pathlib.Path(__file__).parent.resolve()
sys.path.append(baseDir)
from flask import Flask
from flask import render_template
from flask import request
import search
               

app = Flask(__name__, static_folder='static', static_url_path='')

search.load_txt_data()

@app.route( '/conc_test', methods=['GET', 'POST'])
@app.route('/')
def conc_test():
    if request.method == 'POST':
        t = request.form['target'].strip()
        range = [-1*int(request.form['range_bf']), int(request.form['range_af'])]
        context1 = None if len(request.form['context1'].strip())==0 else request.form['context1'].strip()
        context2 = None if len(request.form['context2'].strip())==0 else request.form['context2'].strip()
        excluding = None if len(request.form['excluding'].strip())==0 else request.form['excluding'].strip()

        start = time.perf_counter()
        res = search.search(t, context1_wd=context1, context2_wd=context2, excluding=excluding, range=range)
        print(f"    finished {time.perf_counter() - start:10.5f}[s]")

        search_results = []
        for c in res:
            
            tmp = []
            for rps in c['rel_pos_sub_lst']:
                tmp.append({'pos': rps, 'tag':['<b class="context1">', "</b>"]})
            for rps in c['rel_pos_sub_lst2']:
                tmp.append({'pos': rps, 'tag':['<b class="context2">', "</b>"]})
            
            disp_cxt = search.add_stress_tag2(c['context'], pos_main={'pos': c['rel_pos_found'], 'tag':['<b class="target">', "</b>"]}, pos_sub_lst=tmp)

            search_results.append({'pos':c['pos_found'][0], 'context': disp_cxt, 'file':os.path.basename(c['file']), 'link':f'show_file?file_id={c["file_id"]}&context_begin={c["pos_found"][0]}&context_end={c["pos_found"][1]}#context'})
        
        print(f"--- FOUND LINES: {len(res)} ---")
        return render_template('conc.html', form=request.form, results=search_results)
    else:
        return render_template('conc.html')
        # return redirect(url_for('test'))


@app.route('/show_file')
def show_file(methods=['GET']):
    fid = int(request.args.get('file_id'))
    ctx_b = int(request.args.get('context_begin'))
    ctx_e = int(request.args.get('context_end'))
    return render_template('show_file.html', 
            txt=search.add_stress_tag2(search.ALL_FILE_STR_LIST[fid],
                                       pos_main={'pos':[ctx_b, ctx_e], 
                                                 'tag':['<b class="target" id="context">', "</b>"]}
                )
           )


app.run(port=8000, debug=True)  


