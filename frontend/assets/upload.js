(()=>{
 const $=id=>document.getElementById(id);let selected=null,busy=false,timer;
 function showError(message){$('uploadError').textContent=message;$('uploadError').hidden=false}
 function choose(file){
  if(busy)return;selected=null;$('selection').hidden=true;$('analyze').disabled=true;$('uploadError').hidden=true;
  if(!file)return;
  if(!/\.pdf$/i.test(file.name)){showError('Please choose a PDF file.');return}
  if(file.size===0){showError('This file is empty. Choose another PDF.');return}
  if(file.size>20*1024*1024){showError('Your PDF must be 20 MB or smaller.');return}
  selected=file;$('fileName').textContent=file.name;$('fileSize').textContent=FinLens.number(file.size/1024/1024,2)+' MB';$('selection').hidden=false;$('analyze').disabled=false;
 }
 $('browse').addEventListener('click',()=>$('file').click());$('file').addEventListener('change',()=>choose($('file').files[0]));
 $('remove').addEventListener('click',()=>{choose(null);$('file').value='';$('browse').focus()});
 const zone=$('dropzone');['dragenter','dragover'].forEach(name=>zone.addEventListener(name,event=>{event.preventDefault();if(!busy)zone.classList.add('dragging')}));
 zone.addEventListener('dragleave',event=>{if(!zone.contains(event.relatedTarget))zone.classList.remove('dragging')});
 zone.addEventListener('drop',event=>{event.preventDefault();zone.classList.remove('dragging');if(busy)return;
  if(event.dataTransfer.files.length!==1){choose(null);showError('Drop one PDF at a time.');return}choose(event.dataTransfer.files[0]);
 });
 $('uploadForm').addEventListener('submit',async event=>{
  event.preventDefault();if(!selected||busy)return;busy=true;$('uploadError').hidden=true;$('progress').hidden=false;
  $('uploadForm').setAttribute('aria-busy','true');['browse','file','remove','analyze'].forEach(id=>$(id).disabled=true);
  const start=Date.now();timer=setInterval(()=>{$('progressText').textContent=`Analyzing your report · ${Math.floor((Date.now()-start)/1000)}s elapsed. Please keep this page open.`},1000);
  const form=new FormData();form.append('file',selected);
  try{const result=await FinLens.json('/api/analyze',{method:'POST',body:form});if(!result.id)throw new Error('The analysis has no identifier. Please check History.');busy=false;location.assign('/results/'+encodeURIComponent(result.id))}
  catch(error){showError(error.message+' If the connection was interrupted, check History before uploading again.');}
  finally{clearInterval(timer);busy=false;$('progress').hidden=true;$('uploadForm').removeAttribute('aria-busy');['browse','file','remove','analyze'].forEach(id=>$(id).disabled=false);}
 });
 window.addEventListener('beforeunload',event=>{if(busy){event.preventDefault();event.returnValue=''}});
})();
