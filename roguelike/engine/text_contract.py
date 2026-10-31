"""Reader payload validation shared with saved-room admission, without UI policy."""
def validate_payload(raw, data, path):
    diagnostics=[]
    def error(code,field,message):
        diagnostics.append(dict(severity='error',code=code,field=field,path=path,asset=str(raw.get('id','')) if isinstance(raw,dict) else '',
                                message=message,correction='Correct the saved text definition.'))
    if not isinstance(raw,dict):
        error('TEXT_SHAPE','','Expected one text object.'); return diagnostics
    from engine.location_reports import attachment
    try: attachment(raw)
    except ValueError as exc: error('TEXT_REPORTS','location_reports',str(exc))
    for field in ('title','condition','type','reads_as'):
        if field in raw and not isinstance(raw[field],str): error('TEXT_STRING',field,'Expected a string.')
    if 'lacunae' in raw and type(raw['lacunae']) is not bool: error('TEXT_BOOLEAN','lacunae','Expected a boolean.')
    pages=raw.get('pages')
    if not isinstance(pages,list) or not pages: error('TEXT_PAGES','pages','At least one page object is required.')
    else:
        from engine.text_reader import parse_page
        for index,page in enumerate(pages):
            field=f'pages[{index}]'
            if not isinstance(page,dict): error('TEXT_PAGE',field,'Expected a page object.'); continue
            if not isinstance(page.get('text'),str): error('TEXT_BODY',field+'.text','Expected a string body.')
            else: parse_page(page['text'])
            for key in ('trailing','damaged'):
                if key in page and type(page[key]) is not bool: error('TEXT_BOOLEAN',field+'.'+key,'Expected a boolean.')
    return diagnostics
