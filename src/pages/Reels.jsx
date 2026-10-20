import React,{useEffect,useRef,useState} from "react";
import {Btn,ConfirmDialog,I} from "../components/ui";
import {api,getAccessToken,itemsFrom} from "../api";

const GRADIENTS=["from-violet-600 to-fuchsia-700","from-indigo-600 to-violet-800","from-emerald-600 to-teal-800","from-rose-600 to-purple-800","from-amber-500 to-rose-700","from-sky-600 to-indigo-800"];

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
 const [videoReady,setVideoReady]=useState({});
 const [buffering,setBuffering]=useState({});
 const [videoRetries,setVideoRetries]=useState({});
 const [activeFeed,setActiveFeed]=useState("all");
 const [activeIndex,setActiveIndex]=useState(0);
 const [nextPage,setNextPage]=useState(null);
 const [loadingMore,setLoadingMore]=useState(false);
 const [currentUser,setCurrentUser]=useState(null);
 const [confirmTarget,setConfirmTarget]=useState(null);
 const [confirmBusy,setConfirmBusy]=useState(false);
 const feedRef=useRef(null);
 const loadMoreRef=useRef(null);
 const loadingMoreRef=useRef(false);
 const feedPath=activeFeed==="following"?"/reels/feed/":"/reels/";

 const pageFromNext=next=>{
  if(!next)return null;
  try{return new URL(next,window.location.origin).searchParams.get("page");}
  catch{return null;}
 };

 useEffect(()=>{
  let active=true;
  setLoading(true);
  setError("");
  setReels([]);
  setActiveIndex(0);
  setNextPage(null);
  setVideoErrors({});
  setVideoReady({});
  setBuffering({});
  loadingMoreRef.current=false;
  setCurrentUser(null);
  if(activeFeed==="following"&&!getAccessToken()){
   setLoading(false);
   return()=>{active=false;};
  }
  api.get(feedPath).then(payload=>{
   if(!active)return;
   const list=itemsFrom(payload);
   setReels(list);
   setNextPage(pageFromNext(payload?.next));
   setLiked(Object.fromEntries(list.map(reel=>[reel.id,reel.is_liked])));
   setSaved(Object.fromEntries(list.map(reel=>[reel.id,reel.is_saved])));
  }).catch(reason=>{if(active)setError(reason.message);}).finally(()=>{if(active)setLoading(false);});
  if(getAccessToken())api.get("/auth/me/").then(user=>{if(active)setCurrentUser(user);}).catch(()=>{});
  return()=>{active=false;};
 },[activeFeed,feedPath]);

 const loadMore=async()=>{
  if(!nextPage||loadingMoreRef.current)return;
  loadingMoreRef.current=true;
  setLoadingMore(true);
  try{
   const payload=await api.get(`${feedPath}?page=${encodeURIComponent(nextPage)}`);
   const list=itemsFrom(payload);
   setReels(previous=>[...previous,...list]);
   setLiked(previous=>({...previous,...Object.fromEntries(list.map(reel=>[reel.id,reel.is_liked]))}));
   setSaved(previous=>({...previous,...Object.fromEntries(list.map(reel=>[reel.id,reel.is_saved]))}));
   setNextPage(pageFromNext(payload?.next));
  }catch(reason){setError(reason.message||"Keyingi reellarni yuklab bo'lmadi.");}
  finally{loadingMoreRef.current=false;setLoadingMore(false);}
 };

 useEffect(()=>{
  if(!feedRef.current||!reels.length||typeof IntersectionObserver==="undefined")return;
  const observer=new IntersectionObserver(entries=>{
   const visible=entries.filter(entry=>entry.isIntersecting).sort((first,second)=>second.intersectionRatio-first.intersectionRatio)[0];
   if(visible&&visible.intersectionRatio>=0.5)setActiveIndex(Number(visible.target.dataset.reelIndex));
  },{root:feedRef.current,threshold:[0.25,0.5,0.75]});
  feedRef.current.querySelectorAll(".reel-panel").forEach(panel=>observer.observe(panel));
  return()=>observer.disconnect();
 },[reels]);

 useEffect(()=>{
  if(!feedRef.current)return;
  const videos=feedRef.current.querySelectorAll("video[data-reel-id]");
  videos.forEach(video=>{
   const reelId=Number(video.dataset.reelId);
   const reelIndex=Number(video.dataset.reelIndex);
   if(reelIndex===activeIndex&&!videoErrors[reelId]){
    if(video.readyState<3)setBuffering(previous=>({...previous,[reelId]:true}));
    video.play().then(()=>setPlaying(previous=>({...previous,[reelId]:true}))).catch(()=>setPlaying(previous=>({...previous,[reelId]:false})));
   }else{
    video.pause();
    setPlaying(previous=>previous[reelId]?({...previous,[reelId]:false}):previous);
   }
  });
 },[activeIndex,reels,muted,videoRetries,videoErrors]);

 useEffect(()=>{
  if(!loadMoreRef.current||!nextPage||typeof IntersectionObserver==="undefined")return;
  const observer=new IntersectionObserver(entries=>{
   if(entries.some(entry=>entry.isIntersecting))loadMore();
  },{root:feedRef.current,rootMargin:"800px"});
  observer.observe(loadMoreRef.current);
  return()=>observer.disconnect();
 },[nextPage,loadingMore,activeFeed]);

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
 const deleteReel=async reel=>{
  setConfirmBusy(true);
  try{
   await api.delete(`/reels/${reel.id}/`);
   setReels(previous=>previous.filter(item=>item.id!==reel.id));
   if(comments?.id===reel.id)setComments(null);
   setConfirmTarget(null);
  }catch{setError("Postni o'chirib bo'lmadi. Qayta urinib ko'ring.");}
  finally{setConfirmBusy(false);}
 };
 const deleteComment=async comment=>{
  setConfirmBusy(true);
  try{
   await api.delete(`/comments/${comment.id}/`);
   setCommentItems(previous=>previous.filter(item=>item.id!==comment.id));
   setReels(previous=>previous.map(item=>item.id===comments?.id?{...item,comments_count:Math.max(0,Number(item.comments_count||0)-1)}:item));
   setConfirmTarget(null);
  }catch{setError("Izohni o'chirib bo'lmadi. Qayta urinib ko'ring.");}
  finally{setConfirmBusy(false);}
 };
 const count=value=>Number(value||0).toLocaleString();
 const feedTabs=<div role="tablist" aria-label="Reel lentasi" className="absolute top-3 left-1/2 z-30 flex -translate-x-1/2 gap-1 rounded-full bg-black/60 p-1 text-sm text-white backdrop-blur">
  <button type="button" role="tab" aria-selected={activeFeed==="all"} onClick={()=>setActiveFeed("all")} className={`rounded-full px-4 py-2 font-semibold ${activeFeed==="all"?"bg-white text-black":"text-white"}`}>Tavsiya</button>
  <button type="button" role="tab" aria-selected={activeFeed==="following"} onClick={()=>setActiveFeed("following")} className={`rounded-full px-4 py-2 font-semibold ${activeFeed==="following"?"bg-white text-black":"text-white"}`}>Kuzatilayotganlar</button>
 </div>;

 if(loading)return <div className="relative"><div className="grid min-h-[60dvh] place-items-center" role="status">Reellar yuklanmoqda...</div>{feedTabs}</div>;
 if(!reels.length)return <div className="relative grid min-h-[70dvh] place-items-center px-5 text-center">
    {feedTabs}
    <div>{activeFeed==="following"?<><h1 className="text-2xl font-extrabold mb-2">{getAccessToken()?"Kuzatilayotganlarda reel yo'q":"Kuzatilayotganlar lentasi"}</h1><p className="text-sm text-slate-600 mb-5">{getAccessToken()?"Siz kuzatgan foydalanuvchilar yangi reel joylaganda shu yerda ko'rinadi.":"Kuzatilayotganlar lentasini ko'rish uchun tizimga kiring."}</p>{!getAccessToken()&&<Btn onClick={()=>nav("/login")}>Tizimga kirish</Btn>}</>:<><h1 className="text-2xl font-extrabold mb-2">Hozircha reel yo'q</h1><p className="text-sm text-slate-600 mb-5">Birinchi reelni siz joylang.</p><Btn onClick={()=>nav("/create")}>Reel yaratish</Btn></>}{error&&<p role="alert" className="mt-4 text-sm text-rose-700">{error}</p>}</div>
 </div>;

 return <div className="relative">
  {feedTabs}
  <div ref={feedRef} className="snap h-[100dvh] overflow-y-auto md:m-0">
  {error&&<p role="alert" className="fixed top-4 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-rose-950 px-4 py-2 text-sm text-rose-100">{error}</p>}
  {reels.map((reel,index)=>{
   const videoSource=reel.video_url||reel.video;
   const posterSource=reel.poster_url||reel.poster;
   const isActive=index===activeIndex;
   const hasNearbySource=Math.abs(index-activeIndex)<=1;
   return <div key={reel.id} data-reel-index={index} className="reel-panel snapi h-[100dvh] md:h-[calc(100dvh-2rem)] md:mb-4 md:rounded-3xl relative overflow-hidden flex">
   <div className={`absolute inset-0 bg-gradient-to-br ${GRADIENTS[(reel.id-1)%GRADIENTS.length]} opacity-70`}/>
   <div className="absolute inset-0 bg-gradient-to-t from-black via-black/30 to-black/50 pointer-events-none"/>
    {videoSource&&hasNearbySource&&<video key={`${reel.id}-${videoRetries[reel.id]||0}`} data-reel-id={reel.id} data-reel-index={index} src={videoSource} poster={posterSource||undefined} muted={muted} loop playsInline preload={isActive?"metadata":index===activeIndex+1?"auto":"none"} onLoadStart={()=>{setBuffering(previous=>({...previous,[reel.id]:true}));setVideoReady(previous=>({...previous,[reel.id]:false}));}} onWaiting={()=>setBuffering(previous=>({...previous,[reel.id]:true}))} onCanPlay={()=>{setVideoReady(previous=>({...previous,[reel.id]:true}));setBuffering(previous=>({...previous,[reel.id]:false}));}} onPlaying={()=>setBuffering(previous=>({...previous,[reel.id]:false}))} onPlay={()=>setPlaying(previous=>({...previous,[reel.id]:true}))} onPause={()=>setPlaying(previous=>({...previous,[reel.id]:false}))} onError={()=>{setVideoErrors(previous=>({...previous,[reel.id]:true}));setBuffering(previous=>({...previous,[reel.id]:false}));}} className={`absolute inset-0 h-full w-full bg-black object-contain transition-opacity ${videoErrors[reel.id]?"opacity-0":"opacity-100"}`}/>}
    {videoSource&&!videoReady[reel.id]&&<div aria-hidden="true" className="absolute inset-0 grid place-items-center bg-black">{posterSource?<img src={posterSource} alt="" className="h-full w-full object-contain"/>:<div className={`absolute inset-0 bg-gradient-to-br ${GRADIENTS[(reel.id-1)%GRADIENTS.length]}`}/>}</div>}
    {!reel.video_url&&!reel.video&&<p className="absolute inset-0 grid place-items-center text-sm text-white/80">Bu reelda video mavjud emas.</p>}
    {videoErrors[reel.id]&&<div className="absolute inset-0 z-10 grid place-items-center bg-black/70 p-5 text-center"><div><p role="alert" className="mb-3 text-sm text-white">Video yuklanmadi.</p><Btn type="button" onClick={()=>{setVideoErrors(previous=>({...previous,[reel.id]:false}));setVideoReady(previous=>({...previous,[reel.id]:false}));setBuffering(previous=>({...previous,[reel.id]:true}));setVideoRetries(previous=>({...previous,[reel.id]:(previous[reel.id]||0)+1}));}} cn="px-4 py-2">Qayta urinib ko'ring</Btn></div></div>}
    {buffering[reel.id]&&!videoErrors[reel.id]&&<div role="status" aria-label="Video yuklanmoqda" className="absolute left-1/2 top-1/2 z-10 h-8 w-8 -translate-x-1/2 -translate-y-1/2 animate-spin rounded-full border-2 border-white/35 border-t-white"/>}
   <div className="absolute inset-0 grid place-items-center opacity-90"><div className="h-28 w-28 rounded-[2rem] border border-white/20 bg-white/10 backdrop-blur-sm"><div className="h-full w-full rounded-[2rem] bg-gradient-to-br from-white/20 via-white/5 to-transparent"/></div></div>
   <div className="relative mt-auto p-5 pb-24 md:pb-6 w-full flex items-end gap-4">
    <div className="flex-1 min-w-0">
        {videoSource&&!videoErrors[reel.id]&&<button type="button" onClick={()=>{const video=feedRef.current?.querySelector(`[data-reel-id="${reel.id}"]`);if(!video)return;if(video.paused)video.play().catch(()=>{});else video.pause();}} aria-label={playing[reel.id]?"Videoni pauza qilish":"Videoni ijro etish"} className="mb-3 rounded-full bg-black/50 px-4 py-2 text-sm text-white">{playing[reel.id]?"Pauza":"Ijro"}</button>}
         {videoSource&&!videoErrors[reel.id]&&<button type="button" onClick={()=>setMuted(value=>!value)} aria-label={muted?"Ovoz yoqish":"Ovozni o'chirish"} className="ml-2 rounded-full bg-black/50 px-4 py-2 text-sm text-white">{muted?"Ovoz yoqish":"Ovozni o'chirish"}</button>}
    <button type="button" onClick={()=>reel.author?.username&&nav(`/users/${encodeURIComponent(reel.author.username)}`)} className="text-sm text-white/70 mb-2 hover:text-white">@{reel.author?.username||reel.u||"kitobxon"}</button>
     <h2 className="text-3xl font-extrabold">{reel.t||reel.book?.title}</h2>
     <p className="text-white/70 text-sm">{reel.a||reel.book?.author?.name||""} • {reel.g||reel.book?.genre?.name||reel.book?.genre||""} • {reel.d||""}</p>
     <p className="text-sm text-white/80 mt-2 max-w-md">{reel.cap||reel.caption}</p>
     {reel.book?.id&&<div className="mt-4 flex flex-wrap items-center gap-2">
      <Btn onClick={()=>nav(`/books/${reel.book.id}${reel.book.has_audio?"?play=1":""}`)} cn="inline-flex items-center gap-2 px-6 py-3"><I n={reel.book.has_audio?"play":"book"} f={1} s={16}/>{reel.book.has_audio?"Tinglash":"Kitob haqida"}</Btn>
      {reel.book.has_audio&&reel.book.is_locked&&<span className="inline-flex items-center gap-1 rounded-full bg-amber-400 px-3 py-2 text-xs font-bold text-black"><I n="lock" s={13}/>Premium</span>}
     </div>}
    </div>
    <div className="flex flex-col gap-5 items-center">
     <button onClick={()=>toggleInteraction(reel,"liked")} className="grid gap-1 place-items-center active:scale-90 transition"><span className={`h-11 w-11 rounded-full glass grid place-items-center ${liked[reel.id]?"text-rose-500":""}`}><I n="heart" f={liked[reel.id]?1:0}/></span><span className="text-[11px] text-white/70">{count(reel.likes_count)}</span></button>
     <button onClick={()=>openComments(reel)} className="grid gap-1 place-items-center active:scale-90 transition"><span className="h-11 w-11 rounded-full glass grid place-items-center"><I n="chat"/></span><span className="text-[11px] text-white/70">{count(reel.comments_count)}</span></button>
     <button onClick={()=>toggleInteraction(reel,"saved")} className="grid gap-1 place-items-center active:scale-90 transition"><span className={`h-11 w-11 rounded-full glass grid place-items-center ${saved[reel.id]?"text-rose-500":""}`}><I n="save" f={saved[reel.id]?1:0}/></span><span className="text-[11px] text-white/70">{saved[reel.id]?"Saqlandi":"Saqlash"}</span></button>
     <button onClick={()=>navigator.clipboard?.writeText(location.href)} className="grid gap-1 place-items-center active:scale-90 transition"><span className="h-11 w-11 rounded-full glass grid place-items-center"><I n="share"/></span><span className="text-[11px] text-white/70">Ulash</span></button>
     {String(currentUser?.id)===String(reel.author?.id)&&currentUser?.id&&<button type="button" aria-label="Postni o'chirish" onClick={()=>setConfirmTarget({title:"Postni o'chirish",message:"Postni o'chirishni xohlaysizmi? Bu amalni qaytarib bo'lmaydi.",onConfirm:()=>deleteReel(reel)})} className="grid gap-1 place-items-center active:scale-90 transition"><span className="h-11 w-11 rounded-full bg-rose-600/90 text-white grid place-items-center"><I n="x"/></span><span className="text-[11px] text-white/80">O'chirish</span></button>}
    </div>
   </div>
  </div>})}
  <div ref={loadMoreRef} aria-hidden="true" className="h-1"/>
  {loadingMore&&<p role="status" className="absolute bottom-4 left-1/2 z-20 -translate-x-1/2 rounded-full bg-black/70 px-4 py-2 text-xs text-white">Reellar yuklanmoqda...</p>}
  {comments&&<div className="fixed inset-0 z-50 bg-black/70 flex items-end md:items-center justify-center p-0 md:p-6" onClick={()=>setComments(null)}>
   <div onClick={event=>event.stopPropagation()} className="w-full md:max-w-md bg-[#0d0d16] rounded-t-3xl md:rounded-3xl p-5 border border-white/10">
    <div className="flex justify-between mb-4"><b>Izohlar</b><button onClick={()=>setComments(null)}><I n="x" s={18}/></button></div>
    {commentItems.map(comment=><div key={comment.id} className="flex items-start gap-3 mb-4"><div className="h-9 w-9 rounded-full bg-violet-600/40 shrink-0"/><div className="min-w-0 flex-1"><p className="text-xs text-white/50">@{comment.user?.username||"kitobxon"}</p><p className="text-sm">{comment.text}</p></div>{currentUser?.id&&String(currentUser.id)===String(comment.user?.id)&&<button type="button" aria-label="Izohni o'chirish" onClick={()=>setConfirmTarget({title:"Izohni o'chirish",message:"Izohni o'chirishni xohlaysizmi? Bu amalni qaytarib bo'lmaydi.",onConfirm:()=>deleteComment(comment)})} className="rounded-lg px-2 py-1 text-xs text-rose-300 hover:bg-white/10">O'chirish</button>}</div>)}
    <form onSubmit={submitComment} className="flex gap-2"><input value={commentText} onChange={event=>setCommentText(event.target.value)} placeholder="Izoh yozing..." className="min-w-0 flex-1 glass rounded-xl px-4 py-3 outline-none"/><button type="submit" className="rounded-xl bg-violet-600 px-4 font-bold">Yuborish</button></form>
   </div>
  </div>}
  <ConfirmDialog open={Boolean(confirmTarget)} title={confirmTarget?.title} message={confirmTarget?.message} loading={confirmBusy} onConfirm={confirmTarget?.onConfirm} onCancel={()=>setConfirmTarget(null)}/>
  </div>
 </div>;
}
