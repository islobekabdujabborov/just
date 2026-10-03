import React,{useEffect,useRef,useState} from "react";
import {G} from "../data/mock";
import {Btn,I} from "../components/ui";
import {api,itemsFrom} from "../api";

export default function Reels({nav}){
 const [reels,setReels]=useState([]);
 const [liked,setLiked]=useState({});
 const [saved,setSaved]=useState({});
 const [comments,setComments]=useState(null);
 const [commentItems,setCommentItems]=useState([]);
 const [commentText,setCommentText]=useState("");
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 const [playing,setPlaying]=useState({});
 const [muted,setMuted]=useState(true);
 const [videoErrors,setVideoErrors]=useState({});
 const feedRef=useRef(null);

 useEffect(()=>{
  api.get("/reels/").then(payload=>{
   const list=itemsFrom(payload);
   setReels(list);
   setLiked(Object.fromEntries(list.map(reel=>[reel.id,reel.is_liked])));
   setSaved(Object.fromEntries(list.map(reel=>[reel.id,reel.is_saved])));
  }).catch(reason=>setError(reason.message)).finally(()=>setLoading(false));
 },[]);

 useEffect(()=>{
  if(!feedRef.current||!reels.length||typeof IntersectionObserver==="undefined")return;
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{
   const video=entry.target;
   const reelId=Number(video.dataset.reelId);
   if(entry.isIntersecting){
    video.play().then(()=>setPlaying(previous=>({...previous,[reelId]:true}))).catch(()=>setPlaying(previous=>({...previous,[reelId]:false})));
   }else{
    video.pause();
    setPlaying(previous=>({...previous,[reelId]:false}));
   }
  }),{threshold:0.7});
  feedRef.current.querySelectorAll("video[data-reel-id]").forEach(video=>observer.observe(video));
  return()=>observer.disconnect();
 },[reels]);

 const toggleInteraction=async(reel,key)=>{
  const active=key==="liked"?liked[reel.id]:saved[reel.id];
  const action=key==="liked"?"like":"save";
  try{
   const result=active?await api.delete(`/reels/${reel.id}/${action}/`):await api.post(`/reels/${reel.id}/${action}/`);
   if(key==="liked"){
    setLiked(previous=>({...previous,[reel.id]:result.is_liked}));
    setReels(previous=>previous.map(item=>item.id===reel.id?{...item,likes_count:result.likes_count}:item));
   }else{
    setSaved(previous=>({...previous,[reel.id]:result.is_saved}));
    setReels(previous=>previous.map(item=>item.id===reel.id?{...item,saves_count:result.saves_count}:item));
   }
  }catch(reason){setError(reason.message);}
 };

 const openComments=async reel=>{
  setComments(reel);
  setCommentText("");
  try{setCommentItems(itemsFrom(await api.get(`/reels/${reel.id}/comments/`)));}
  catch(reason){setError(reason.message);setCommentItems([]);}
 };
 const submitComment=async event=>{
  event.preventDefault();
  if(!commentText.trim())return;
  try{
   const created=await api.post(`/reels/${comments.id}/comments/`,{text:commentText.trim()});
   setCommentItems(previous=>[...previous,created]);
   setCommentText("");
  }catch(reason){setError(reason.message);}
 };
 const count=value=>Number(value||0).toLocaleString();

 if(loading)return <div className="grid min-h-[60dvh] place-items-center" role="status">Reellar yuklanmoqda...</div>;
 if(!reels.length)return <div className="grid min-h-[70dvh] place-items-center px-5 text-center">
    <div><h1 className="text-2xl font-extrabold mb-2">Hozircha reel yo'q</h1><p className="text-sm text-slate-600 mb-5">Birinchi reelni siz joylang.</p><Btn onClick={()=>nav("/create")}>Reel yaratish</Btn>{error&&<p role="alert" className="mt-4 text-sm text-rose-700">{error}</p>}</div>
 </div>;

 return <div ref={feedRef} className="snap h-[100dvh] overflow-y-auto md:m-0">
  {error&&<p role="alert" className="fixed top-4 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-rose-950 px-4 py-2 text-sm text-rose-100">{error}</p>}
  {reels.map(reel=><div key={reel.id} className="snapi h-[100dvh] md:h-[calc(100dvh-2rem)] md:mb-4 md:rounded-3xl relative overflow-hidden flex">
   <div className={`absolute inset-0 bg-gradient-to-br ${G[(reel.id-1)%6]} opacity-70`}/>
   <div className="absolute inset-0 bg-gradient-to-t from-black via-black/30 to-black/50"/>
    {reel.video_url||reel.video?<video data-reel-id={reel.id} src={reel.video_url||reel.video} muted={muted} loop playsInline preload="none" onPlay={()=>setPlaying(previous=>({...previous,[reel.id]:true}))} onPause={()=>setPlaying(previous=>({...previous,[reel.id]:false}))} onError={()=>setVideoErrors(previous=>({...previous,[reel.id]:true}))} className={`absolute inset-0 h-full w-full object-cover ${videoErrors[reel.id]?"hidden":""}`}/>:null}
    {!reel.video_url&&!reel.video&&<p className="absolute inset-0 grid place-items-center text-sm text-white/80">Bu reelda video mavjud emas.</p>}
   <div className="absolute inset-0 grid place-items-center opacity-90"><div className="h-28 w-28 rounded-[2rem] border border-white/20 bg-white/10 backdrop-blur-sm"><div className="h-full w-full rounded-[2rem] bg-gradient-to-br from-white/20 via-white/5 to-transparent"/></div></div>
   <div className="relative mt-auto p-5 pb-24 md:pb-6 w-full flex items-end gap-4">
    <div className="flex-1 min-w-0">
        {(reel.video_url||reel.video)&&!videoErrors[reel.id]&&<button type="button" onClick={()=>{const video=feedRef.current?.querySelector(`[data-reel-id="${reel.id}"]`);if(!video)return;if(video.paused)video.play().catch(()=>{});else video.pause();}} aria-label={playing[reel.id]?"Videoni pauza qilish":"Videoni ijro etish"} className="mb-3 rounded-full bg-black/50 px-4 py-2 text-sm text-white">{playing[reel.id]?"Pauza":"Ijro"}</button>}
         {(reel.video_url||reel.video)&&!videoErrors[reel.id]&&<button type="button" onClick={()=>setMuted(value=>!value)} aria-label={muted?"Ovoz yoqish":"Ovozni o'chirish"} className="ml-2 rounded-full bg-black/50 px-4 py-2 text-sm text-white">{muted?"Ovoz yoqish":"Ovozni o'chirish"}</button>}
         {videoErrors[reel.id]&&<p role="status" className="text-sm text-white/80 mb-2">Video yuklanmadi.</p>}
    <button type="button" onClick={()=>reel.author?.username&&nav(`/users/${encodeURIComponent(reel.author.username)}`)} className="text-sm text-white/70 mb-2 hover:text-white">@{reel.author?.username||reel.u||"kitobxon"}</button>
     <h2 className="text-3xl font-extrabold">{reel.t||reel.book?.title}</h2>
     <p className="text-white/70 text-sm">{reel.a||reel.book?.author?.name||""} • {reel.g||reel.book?.genre?.name||reel.book?.genre||""} • {reel.d||""}</p>
     <p className="text-sm text-white/80 mt-2 max-w-md">{reel.cap||reel.caption}</p>
     <Btn onClick={()=>nav("/books/"+(reel.book?.id||reel.id))} cn="px-6 py-3 mt-4 inline-flex items-center gap-2"><I n="play" f={1} s={16}/>Kitobni tinglash</Btn>
    </div>
    <div className="flex flex-col gap-5 items-center">
     <button onClick={()=>toggleInteraction(reel,"liked")} className="grid gap-1 place-items-center active:scale-90 transition"><span className={`h-11 w-11 rounded-full glass grid place-items-center ${liked[reel.id]?"text-rose-500":""}`}><I n="heart" f={liked[reel.id]?1:0}/></span><span className="text-[11px] text-white/70">{count(reel.likes_count)}</span></button>
     <button onClick={()=>openComments(reel)} className="grid gap-1 place-items-center active:scale-90 transition"><span className="h-11 w-11 rounded-full glass grid place-items-center"><I n="chat"/></span><span className="text-[11px] text-white/70">{count(reel.comments_count)}</span></button>
     <button onClick={()=>toggleInteraction(reel,"saved")} className="grid gap-1 place-items-center active:scale-90 transition"><span className={`h-11 w-11 rounded-full glass grid place-items-center ${saved[reel.id]?"text-rose-500":""}`}><I n="save" f={saved[reel.id]?1:0}/></span><span className="text-[11px] text-white/70">{saved[reel.id]?"Saqlandi":"Saqlash"}</span></button>
     <button onClick={()=>navigator.clipboard?.writeText(location.href)} className="grid gap-1 place-items-center active:scale-90 transition"><span className="h-11 w-11 rounded-full glass grid place-items-center"><I n="share"/></span><span className="text-[11px] text-white/70">Ulash</span></button>
    </div>
   </div>
  </div>)}
  {comments&&<div className="fixed inset-0 z-50 bg-black/70 flex items-end md:items-center justify-center p-0 md:p-6" onClick={()=>setComments(null)}>
   <div onClick={event=>event.stopPropagation()} className="w-full md:max-w-md bg-[#0d0d16] rounded-t-3xl md:rounded-3xl p-5 border border-white/10">
    <div className="flex justify-between mb-4"><b>Izohlar</b><button onClick={()=>setComments(null)}><I n="x" s={18}/></button></div>
    {commentItems.map(comment=><div key={comment.id} className="flex gap-3 mb-4"><div className="h-9 w-9 rounded-full bg-violet-600/40 shrink-0"/><div><p className="text-xs text-white/50">@{comment.user?.username||"kitobxon"}</p><p className="text-sm">{comment.text}</p></div></div>)}
    <form onSubmit={submitComment} className="flex gap-2"><input value={commentText} onChange={event=>setCommentText(event.target.value)} placeholder="Izoh yozing..." className="min-w-0 flex-1 glass rounded-xl px-4 py-3 outline-none"/><button type="submit" className="rounded-xl bg-violet-600 px-4 font-bold">Yuborish</button></form>
   </div>
  </div>}
 </div>;
}
