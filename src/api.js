const API_URL=(import.meta.env.VITE_API_URL||"/api").replace(/\/$/,"");
const ACCESS_KEY="avobook.access";
const REFRESH_KEY="avobook.refresh";

export const getAccessToken=()=>localStorage.getItem(ACCESS_KEY);
export const saveTokens=({access,refresh})=>{
 if(access)localStorage.setItem(ACCESS_KEY,access);
 if(refresh)localStorage.setItem(REFRESH_KEY,refresh);
};
export const clearTokens=()=>{
 localStorage.removeItem(ACCESS_KEY);
 localStorage.removeItem(REFRESH_KEY);
};

const flattenErrors=value=>{
 if(typeof value==="string")return value;
 if(Array.isArray(value))return value.map(flattenErrors).filter(Boolean).join(" ");
 if(value&&typeof value==="object")return Object.values(value).map(flattenErrors).filter(Boolean).join(" ");
 return "";
};

async function request(path,{method="GET",body,headers={},retry=true}={}){
 const token=getAccessToken();
 const response=await fetch(`${API_URL}${path}`,{
  method,
  headers:{...(body instanceof FormData?{}:{"Content-Type":"application/json"}),...(token?{Authorization:`Bearer ${token}`}:{ }),...headers},
  body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)
 });
 if(response.status===401&&retry){
  const refreshToken=localStorage.getItem(REFRESH_KEY);
  if(refreshToken){
   const refreshResponse=await fetch(`${API_URL}/auth/refresh/`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({refresh:refreshToken})});
   if(refreshResponse.ok){saveTokens(await refreshResponse.json());return request(path,{method,body,headers,retry:false});}
  }
  clearTokens();
 }
 if(!response.ok){
  const payload=await response.json().catch(()=>null);
  throw new Error(flattenErrors(payload)||`So'rov bajarilmadi (${response.status}). ${response.statusText||""}`.trim());
 }
 if(response.status===204)return null;
 return response.json();
}

export function uploadWithProgress(path,body,onProgress=()=>{}){
 let xhr=null;
 let cancelled=false;
 let rejectPromise;
 const promise=new Promise((resolve,reject)=>{
  rejectPromise=reject;
  const send=async retry=>{
   if(cancelled)return;
   xhr=new XMLHttpRequest();
   xhr.open("POST",`${API_URL}${path}`);
   const token=getAccessToken();
   if(token)xhr.setRequestHeader("Authorization",`Bearer ${token}`);
   xhr.upload.onprogress=event=>{
    if(event.lengthComputable)onProgress(Math.round(event.loaded/event.total*100));
   };
   xhr.onerror=()=>reject(new Error("Internet aloqasini tekshirib, qayta urinib ko'ring."));
   xhr.onabort=()=>reject(new DOMException("Yuklash bekor qilindi.","AbortError"));
   xhr.onload=async()=>{
    if(xhr.status===401&&retry){
     const refreshToken=localStorage.getItem(REFRESH_KEY);
     if(refreshToken){
      try{
       const response=await fetch(`${API_URL}/auth/refresh/`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({refresh:refreshToken})});
       if(response.ok){saveTokens(await response.json());send(false);return;}
      }catch(error){
       reject(new Error("Sessiya muddati tugadi. Qayta tizimga kiring."));
       return;
      }
     }
     clearTokens();
    }
    let payload=null;
    try{payload=JSON.parse(xhr.responseText);}catch{}
    if(xhr.status<200||xhr.status>=300){
     reject(new Error(flattenErrors(payload)||`So'rov bajarilmadi (${xhr.status}).`));
     return;
    }
    resolve(payload);
   };
   xhr.send(body);
  };
  send(true);
 });
 return {promise,cancel:()=>{
  cancelled=true;
  xhr?.abort();
  rejectPromise(new DOMException("Yuklash bekor qilindi.","AbortError"));
 }};
}

export const api={
 get:(path)=>request(path),
 post:(path,data)=>request(path,{method:"POST",body:data}),
 put:(path,data)=>request(path,{method:"PUT",body:data}),
 patch:(path,data)=>request(path,{method:"PATCH",body:data}),
 delete:(path)=>request(path,{method:"DELETE"}),
};
export const itemsFrom=payload=>Array.isArray(payload)?payload:(payload?.results||[]);
export const fileUrl=value=>value||"";
