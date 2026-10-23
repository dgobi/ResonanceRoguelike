/* Lossless JSON value model. UI defaults never enter imported documents. */
'use strict';
(function (root) {
  function strictParse(text) {
    let at = 0;
    const fail = message => { throw new Error(`${message} at character ${at}`); };
    const space = () => { while (/[ \t\r\n]/.test(text[at] || '') && at < text.length) at++; };
    function string() {
      const start = at++;
      while (at < text.length) {
        const ch = text[at++];
        if (ch === '\\') { at++; continue; }
        if (ch === '"') return JSON.parse(text.slice(start, at));
      }
      fail('Unterminated string');
    }
    function decimal(token) {
      let [mantissa, exponent = '0'] = token.toLowerCase().split('e');
      let sign = '';
      if (mantissa[0] === '-') { sign = '-'; mantissa = mantissa.slice(1); }
      const pieces = mantissa.split('.');
      let digits = pieces.join('').replace(/^0+/, '');
      let scale = Number(exponent) - (pieces[1] || '').length;
      while (digits.endsWith('0')) { digits = digits.slice(0, -1); scale++; }
      return digits ? `${sign}${digits}e${scale}` : '0';
    }
    function value() {
      space(); const ch = text[at];
      if (ch === '"') return string();
      if (ch === '{') {
        at++; space(); const result = Object.create(null), keys = new Set();
        if (text[at] === '}') { at++; return result; }
        while (true) {
          space(); if (text[at] !== '"') fail('Expected object key');
          const key = string(); if (keys.has(key)) fail(`Duplicate key ${key}`);
          keys.add(key); space(); if (text[at++] !== ':') fail('Expected colon');
          result[key] = value(); space();
          if (text[at] === '}') { at++; return result; }
          if (text[at++] !== ',') fail('Expected comma');
        }
      }
      if (ch === '[') {
        at++; space(); const result = [];
        if (text[at] === ']') { at++; return result; }
        while (true) {
          result.push(value()); space();
          if (text[at] === ']') { at++; return result; }
          if (text[at++] !== ',') fail('Expected comma');
        }
      }
      for (const [word, result] of [['null', null], ['true', true], ['false', false]]) {
        if (text.slice(at, at + word.length) === word) { at += word.length; return result; }
      }
      const match = text.slice(at).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
      if (!match) fail('Invalid JSON value');
      const token = match[0], number = Number(token);
      if (!Number.isFinite(number) || Object.is(number, -0) || Math.abs(number) > Number.MAX_SAFE_INTEGER ||
          decimal(token) !== decimal(String(number))) fail('Number cannot be preserved faithfully; use a supported number or retain it outside this editor');
      at += token.length; return number;
    }
    const result = value(); space();
    if (at !== text.length) fail('Unexpected trailing input');
    return result;
  }
  const clone = value => strictParse(JSON.stringify(value));
  const gridKey = doc => Object.hasOwn(doc, 'layers') ? 'layers' : Object.hasOwn(doc, 'layout') ? 'layout' : 'layers';
  function dimensions(doc) {
    const rows = doc?.[gridKey(doc)] || [];
    return { width: Array.isArray(rows) ? Math.max(0, ...rows.map(r => typeof r === 'string' ? [...r].length : 0)) : 0,
      height: Array.isArray(rows) ? rows.length : 0 };
  }
  class DocumentModel {
    constructor() { this.doc = null; this.route = 'ordinary_building'; this.category = 'residential'; this.past = []; this.future = []; }
    state() { return clone({doc: this.doc, route: this.route, category: this.category}); }
    restore(state) { Object.assign(this, clone(state)); }
    importText(text, route = this.route, category = this.category) {
      const doc = strictParse(text);
      if (!doc || Array.isArray(doc) || typeof doc !== 'object') throw new Error('A structure must be one JSON object. Current document unchanged.');
      this.past.push(this.state()); this.future = [];
      this.doc = doc; this.route = route; this.category = category;
    }
    change(action) {
      if (!this.doc) throw new Error('Import or create a document first.');
      const before = this.state(), next = clone(this.doc);
      action(next); // Atomic: a failed edit cannot mutate the document or history.
      this.past.push(before); this.future = []; this.doc = next;
    }
    exportText() {
      if (!this.doc) throw new Error('No document loaded.');
      return JSON.stringify(this.doc, null, 2) + '\n';
    }
    undo() { if (this.past.length) { this.future.push(this.state()); this.restore(this.past.pop()); } }
    redo() { if (this.future.length) { this.past.push(this.state()); this.restore(this.future.pop()); } }
    editable() {
      const {width, height} = dimensions(this.doc);
      return width > 0 && height > 0 && width <= 256 && height <= 256 &&
        this.doc[gridKey(this.doc)].every(row => typeof row === 'string');
    }
    paint(x, y, layer, value) {
      if (!this.editable()) throw new Error('Grid editing supports 1..256 on each axis. Document remains intact for export.');
      this.change(doc => {
        const rows = doc[gridKey(doc)], {width,height} = dimensions(doc);
        if (!Number.isInteger(x) || !Number.isInteger(y) || x<0 || y<0 || x>=width || y>=height) throw new Error('Outside grid.');
        if (layer === 'terrain') {
          if (!Object.hasOwn(doc.legend || {}, value) || [...value].length !== 1) throw new Error('Choose a defined terrain legend character.');
          const row = [...rows[y]];
          if (x >= row.length) throw new Error('This ragged cell is absent. Resize explicitly with null padding first.');
          row[x] = value; rows[y] = row.join('');
        } else {
          if (value !== null && typeof value !== 'string') throw new Error('Decor must be a full ID or null.');
          if (!Object.hasOwn(doc, 'decor_layer')) doc.decor_layer = Array.from({length:height}, () => Array(width).fill(null));
          if (!Array.isArray(doc.decor_layer) || doc.decor_layer.length !== height ||
              doc.decor_layer.some(r => !Array.isArray(r) || r.length !== width)) throw new Error('Repair invalid decor arrays explicitly before painting.');
          doc.decor_layer[y][x] = value;
        }
      });
    }
    setLegend(legend) {
      this.change(doc => {
        if (!legend || Array.isArray(legend) || typeof legend !== 'object' ||
            Object.entries(legend).some(([k,v]) => [...k].length !== 1 || v !== null && typeof v !== 'string')) throw new Error('Legend needs single-character keys and terrain IDs/null.');
        for (const row of doc[gridKey(doc)] || []) for (const char of row) {
          if (!Object.hasOwn(legend,char)) throw new Error(`Cannot delete used legend character ${JSON.stringify(char)}. Repaint those cells first.`);
        }
        doc.legend = clone(legend);
      });
    }
    setField(field, value, remove=false) {
      if (['layers','layout','decor_layer','legend','width','height','__proto__','constructor','prototype'].includes(field)) throw new Error('Use the dedicated geometry/layer controls for this field.');
      this.change(doc => { if (remove) delete doc[field]; else doc[field] = clone(value); });
    }
    setSpecial(index, row, remove=false) {
      this.change(doc => {
        const rows = doc.special_tiles === undefined ? [] : doc.special_tiles;
        if (!Array.isArray(rows) || index<0 || index>rows.length) throw new Error('Select a special record.');
        if (remove && index>=rows.length) throw new Error('No existing record selected; document unchanged.');
        if (!remove && (!row || Array.isArray(row) || typeof row !== 'object')) throw new Error('Special must be an object.');
        if (!remove && (!Number.isInteger(row.x) || !Number.isInteger(row.y))) throw new Error('Special needs integer source x and y.');
        if (remove) rows.splice(index,1); else rows[index] = clone(row);
        doc.special_tiles = rows;
      });
    }
    resizeImpact(width,height) {
      const doc=this.doc, old=dimensions(doc), affected=[];
      for (const [y,row] of (doc?.[gridKey(doc)] || []).entries()) {
        if (y>=height || [...row].length>width) affected.push(`terrain row ${y}`);
      }
      if (doc.decor_layer && (old.width>width || old.height>height)) affected.push('decor grid');
      for (const field of ['special_tiles','player_start','stairs_up','connection_point','spawn_offset','anchors','access_targets']) {
        const rows=Array.isArray(doc[field]) ? doc[field] : doc[field] ? [doc[field]] : [];
        rows.forEach((r,n) => { if (r && (r.x>=width || r.y>=height)) affected.push(`${field}[${n}] at (${r.x},${r.y})`); });
      }
      return {old,width,height,affected,unknown:'Unknown coordinate-bearing metadata is preserved unchanged; review it after any geometry edit.'};
    }
    resize(width,height) {
      if (!Number.isInteger(width) || !Number.isInteger(height) || width<1 || height<1 || width>256 || height>256) throw new Error('Editing dimensions must be integers in 1..256; original document is preserved.');
      const impact=this.resizeImpact(width,height);
      if (width<impact.old.width || height<impact.old.height) throw new Error('Crop refused. Affected: '+impact.affected.join('; ')+'. Export the intact draft; no records were removed.');
      this.change(doc => {
        if (!doc.legend || typeof doc.legend!=='object' || Array.isArray(doc.legend)) throw new Error('Define a valid legend before resize.');
        let pad=Object.keys(doc.legend).find(k => doc.legend[k]===null);
        if (pad===undefined) {
          pad=[' ','~','_','`'].find(k => !Object.hasOwn(doc.legend,k));
          if (pad===undefined) throw new Error('Add a null-mapped legend character before enlargement.');
          doc.legend[pad]=null;
        }
        const key=gridKey(doc), rows=doc[key];
        if (!Array.isArray(rows) || rows.some(r => typeof r!=='string')) throw new Error('Repair terrain rows before resizing.');
        doc[key]=Array.from({length:height},(_,y) => {
          const row=[...(rows[y] || '')]; return row.concat(Array(width-row.length).fill(pad)).join('');
        });
        if (Object.hasOwn(doc,'decor_layer')) {
          if (!Array.isArray(doc.decor_layer) || doc.decor_layer.some(r => !Array.isArray(r))) throw new Error('Repair decor arrays before resize.');
          if (doc.decor_layer.length>height || doc.decor_layer.some(r => r.length>width)) throw new Error('Resize would crop existing decor outside the terrain extent. Repair that mismatch explicitly; document unchanged.');
          doc.decor_layer=Array.from({length:height},(_,y) => Array.from({length:width},(_,x) => doc.decor_layer[y]?.[x] ?? null));
        }
        if (Object.hasOwn(doc,'width')) doc.width=width;
        if (Object.hasOwn(doc,'height')) doc.height=height;
      });
      return impact;
    }
  }
  root.StructureEditor = {strictParse, DocumentModel, dimensions, gridKey};
  if (typeof module !== 'undefined') module.exports = root.StructureEditor;
})(typeof window === 'undefined' ? globalThis : window);
