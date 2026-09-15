"""Reuse the production navigation markup and its CSS on standalone pages."""
import re

def header_css(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    output=[];i=0
    while i<len(text):
        a=text.find('{',i)
        if a<0:break
        depth=1;b=a+1
        while b<len(text) and depth:
            depth+=(text[b]=='{')-(text[b]=='}');b+=1
        selector=text[i:a].strip();body=text[a+1:b-1]
        if selector.startswith('@media'):
            inner=header_css(body)
            if inner:output.append(selector+'{'+inner+'}')
        elif any(x in selector for x in ('.topbar','.brand','.github')):output.append(selector+'{'+body+'}')
        i=b
    return '\n'.join(output)

def apply_shared_header(source,output):
    main=(source/'index.html').read_text();header='<header class="topbar">'+main.split('<header class="topbar">',1)[1].split('</header>',1)[0]+'</header>'
    header=header.replace('href="#','href="../#').replace('href="./trends/"','href="./" class="active" aria-current="page"').replace('src="./benchmark','src="../benchmark')
    p=output/'trends/index.html';s=p.read_text();s=re.sub(r'<!-- SITE_HEADER_START -->.*?<!-- SITE_HEADER_END -->','<!-- SITE_HEADER_START -->'+header+'<!-- SITE_HEADER_END -->',s,flags=re.S);p.write_text(s)
    (output/'site-header.css').write_text(header_css((source/'styles.css').read_text()))
