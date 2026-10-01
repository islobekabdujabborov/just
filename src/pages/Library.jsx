    import React,{useEffect,useState} from "react";
import {api,itemsFrom} from "../api";
import {Card} from "../components/ui";

const TAB_ENDPOINTS=["/library/liked/","/library/saved/","/library/history/","/library/"];
const TAB_NAMES=["Yoqtirganlar","Saqlanganlar","Tinglash tarixi","Kitoblarim"];
export default function Library({nav}){
 const [selected,setSelected]=useState(0);
 const [books,setBooks]=useState([]);
 const [error,setError]=useState("");
 useEffect(()=>{api.get(TAB_ENDPOINTS[selected]).then(payload=>{
  const records=itemsFrom(payload);
  const flattened=records.map(record=>record.book||record);
  setBooks(selected===3&&payload.my_books?payload.my_books:flattened);
 }).catch(reason=>{setBooks([]);setError(reason.message);});},[selected]);
 return <div><h1 className="text-3xl font-extrabold mb-5">Kutubxona</h1>
  <div className="flex gap-2 mb-6 overflow-x-auto">{TAB_NAMES.map((tab,index)=><button key={tab} onClick={()=>setSelected(index)} className={`shrink-0 px-4 py-2 rounded-full text-sm font-semibold ${index===selected?"bg-violet-600":"glass"}`}>{tab}</button>)}</div>
  {error&&<p role="alert" className="text-sm text-rose-300 mb-4">{error}</p>}
  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">{books.map(book=><div key={book.id}><Card b={book} nav={nav}/>{book.percentage!==undefined&&<><div className="h-1 bg-white/10 rounded-full mt-2"><div className="h-full bg-violet-500 rounded-full" style={{width:`${book.percentage}%`}}/></div><p className="text-[11px] text-white/40 mt-1">{book.percentage}% tinglangan</p></>}</div>)}</div>
 </div>;
}
