import React, {useEffect,useRef,useState} from 'react';
const groups=[['Humanities Elective','HuEl'],['Discipline Elective','DEL'],['Open Elective','OpEl']];
export default function CompletedElectivesDialog({open,semester,courses,completed,onSave,onCancel}) {
 const ref=useRef(null),[selected,setSelected]=useState([]),[query,setQuery]=useState(''),[category,setCategory]=useState('Humanities Elective');
 useEffect(()=>{if(open){setSelected(completed);setQuery('');ref.current?.showModal();}else ref.current?.close();},[open]);
 const pool=courses.filter(c=>groups.some(([g])=>g===c.category));
 return <dialog ref={ref} onCancel={e=>{e.preventDefault();onCancel();}} className="rounded-xl p-5 w-[min(94vw,850px)] max-h-[90vh] backdrop:bg-slate-900/40" aria-label="Completed electives">
 <h2 className="text-xl font-bold">Which electives did you complete through semester {semester}?</h2>
 <p className="my-3 text-sm">Check only courses you passed. These credits count toward graduation and will not be scheduled again. Leave unchecked if you completed none.</p>
 <div className="flex flex-wrap gap-2">{groups.map(([g,label])=><button key={g} onClick={()=>setCategory(g)} className="border rounded p-2" aria-pressed={category===g}>{label} · {pool.filter(c=>c.category===g&&selected.includes(c.code)).length} completed</button>)}</div>
 <input aria-label="Search completed electives" placeholder="Search course code or title" value={query} onChange={e=>setQuery(e.target.value)} className="border rounded p-2 w-full my-3"/>
 <div className="space-y-2">{pool.filter(c=>c.category===category&&`${c.code} ${c.title}`.toLowerCase().includes(query.toLowerCase())).map(c=><label key={c.code} className="flex gap-3 border rounded p-2 text-sm"><input type="checkbox" checked={selected.includes(c.code)} onChange={()=>setSelected(prev=>prev.includes(c.code)?prev.filter(x=>x!==c.code):[...prev,c.code])}/><span><strong>{c.code}</strong> · {c.title} · {c.credits} credits</span></label>)}</div>
 <div className="sticky bottom-0 bg-white py-3 flex gap-3"><button className="border rounded p-2" onClick={onCancel}>Review later</button><button className="border rounded p-2" onClick={()=>onSave(selected,false)}>Save completed electives</button><button className="bg-blue-600 text-white rounded p-2" onClick={()=>onSave(selected,true)}>Save and generate remaining plan</button></div>
 </dialog>
}
