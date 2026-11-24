/* Local VFM research UI; uses the existing authenticated relative API. */
(() => {
  const el=id=>document.getElementById(id);
  let preview=null;
  const t=(nl,en)=>document.documentElement.lang==='en'||(typeof cfg!=='undefined'&&cfg?.language==='en')?en:nl;
  const say=(id,value)=>{el(id).textContent=value;};
  const reset=()=>{preview=null;el('vfmDownload').disabled=true;say('vfmSample','');};
  const run=async(fn)=>{try{await fn();}catch(e){say('vfmStatus',e.message);msg(e.message,true);}};
  async function open(){
    say('vfmIntro',t('Experimenteel, uitsluitend lokale analyse. Geen regeling of vervanging van gemeten flow/COP. Koppel ook de status ruimteverwarming, defrost en eventueel pomp PWM.','Experimental local analysis only. No control or replacement of measured flow/COP. Map space heating, defrost and optional pump PWM.'));
    say('vfmEnabledLabel',t('Research inschakelen','Enable research'));
    say('vfmConfirmedLabel',t('Ik bevestig echte actieve vermogensmeting, correcte verwarmingsstatus, BUH-grens, waterfactor en (voor export) fysieke flowmeting.','I confirm metered active power, valid heating mode, BUH boundary, fluid factor and (for export) a physical flow meter.'));
    for(const [id,nl,en] of [['vfmSave','Opslaan','Save'],['vfmExportTitle','Referentiedata exporteren','Export reference data'],['vfmPeriodLabel','Periode','Window'],['vfmPreview','Voorbeeld maken','Preview'],['vfmDownload','CSV downloaden','Download CSV'],['vfmModelTitle','Lokaal model trainen en beoordelen','Train and evaluate local model'],['vfmTrain','Trainen','Train'],['vfmReport','Schatting tonen','Show estimate']])say(id,t(nl,en));
    const s=await api('research/settings');el('vfmEnabled').checked=s.enabled;el('vfmConfirmed').checked=s.confirmed;reset();
  }
  el('researchNav').addEventListener('click',()=>run(open));
  el('vfmSave').onclick=()=>run(async()=>{await api('research/settings',{enabled:el('vfmEnabled').checked,confirmed:el('vfmConfirmed').checked});reset();say('vfmStatus',t('Opgeslagen.','Saved.'));});
  el('vfmHours').onchange=reset;
  el('vfmPreview').onclick=()=>run(async()=>{reset();preview=await api('research/export?hours='+el('vfmHours').value);say('vfmExportStatus',`${preview.row_count} ${t('geschikte minuten; geen automatische upload. Deel alleen na controle.','eligible minutes; no automatic upload. Review before sharing.')}`);say('vfmSample',preview.csv.split('\n').slice(0,11).join('\n'));el('vfmDownload').disabled=!preview.row_count;});
  el('vfmDownload').onclick=()=>{if(!preview)return;const url=URL.createObjectURL(new Blob([preview.csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='ohpa-vfm-reference.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  el('vfmTrain').onclick=()=>run(async()=>{
    const files=[...el('vfmFiles').files];if(!files.length)throw Error(t('Selecteer CSV-bestanden.','Select CSV files.'));if(files.reduce((sum,f)=>sum+f.size,0)>12000000)throw Error('CSV limit 12 MB');
    const parts=await Promise.all(files.map(f=>f.text()));const header=parts[0].split(/\r?\n/)[0];if(parts.some(p=>p.split(/\r?\n/)[0]!==header))throw Error('CSV headers differ');
    const csv=header+'\n'+parts.map(p=>p.split(/\r?\n/).slice(1).filter(Boolean).join('\n')).join('\n');
    say('vfmStatus',t('Trainen…','Training…'));const artifact=await api('research/train',{csv,method:el('vfmMethod').value});say('vfmStatus',`${artifact.installation_count} ${t('installaties; experimenteel model opgeslagen.','installations; experimental model saved.')}`);say('vfmValidation',JSON.stringify(artifact.validation,null,2));
  });
  el('vfmReport').onclick=()=>run(async()=>{
    const r=await api('research/report?hours='+el('vfmHours').value+'&method='+el('vfmMethod').value);const p=r.latest;
    el('vfmCards').innerHTML=[card(t('Geschatte gemiddelde flow','Estimated mean flow'),fmt(r.mean_flow_lh,0),'L/h'),card(t('Laatste geschatte flow','Latest estimated flow'),fmt(p?.flow_lh,0),'L/h'),card(t('Gemeten flow bij laatste schatting','Measured flow at latest estimate'),fmt(p?.measured_flow_lh,0),'L/h'),card(t('Geschatte COP','Estimated COP'),fmt(p?.cop_estimated)),card(t('Geschatte minuten','Predicted minutes'),`${r.predicted_minutes}/${r.window_minutes}`)].join('');
    say('vfmStatus',r.model?(p?.reason||t('Experimenteel; geen onafhankelijke COP-meting.','Experimental; not an independent COP measurement.')):t('Geen getraind model voor deze methode.','No trained model for this method.'));
    say('vfmValidation',r.model?JSON.stringify({installations:r.model.installation_count,validation:r.model.validation,worst_installation_p90_relative_error:r.model.error_fraction_p90_worst_installation},null,2):'');
  });
})();
