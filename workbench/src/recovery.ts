export type RecoveredDraft = {key:string; generation:number; draft:string; variant:boolean; variant_id:string; published?:{path:string;after_sha256:string;generation:number}|null};
export type RecoveryControl = {flush:()=>Promise<void>; discard:()=>Promise<void>; handoff:()=>string|undefined; owner:()=>string};
export type RegisterRecovery = (token:string,control:RecoveryControl)=>()=>void;
export type RecoveryStatus = {state:"pending"|"saved"|"error";generation:number;message?:string};

// One ordered checkpoint path per mounted owner. The timer is not reset by
// typing, so continuous input also checkpoints within 500 ms of acceptance.
export class Checkpoints {
  private wanted=0;
  private durable=0;
  private timer:ReturnType<typeof setTimeout>|undefined;
  private running:Promise<void>|null=null;
  private stopped=false;
  constructor(private write:()=>Promise<{generation:number}>,private notify:(s:RecoveryStatus)=>void,private delay=500){}
  accepted(generation:number){
    if(this.stopped || generation<=this.wanted)return;
    this.wanted=generation;this.notify({state:"pending",generation});
    if(!this.timer)this.timer=setTimeout(()=>{this.timer=undefined;void this.flush().catch(()=>{});},this.delay);
  }
  async flush():Promise<void>{
    if(this.timer){clearTimeout(this.timer);this.timer=undefined;}
    if(this.running){await this.running;return this.flush();}
    if(this.stopped || this.durable>=this.wanted)return;
    this.running=(async()=>{
      try{
        while(!this.stopped && this.durable<this.wanted){
          const wanted=this.wanted;
          const result=await this.write();
          if(result.generation<wanted)throw new Error("A newer accepted edit still needs a checkpoint. Retry recovery save.");
          this.durable=Math.max(this.durable,result.generation);
        }
        if(!this.stopped)this.notify({state:"saved",generation:this.durable});
      }catch(e){if(!this.stopped)this.notify({state:"error",generation:this.wanted,message:String((e as {message?:string}).message || e)});throw e;}
    })();
    try{await this.running;}finally{this.running=null;}
  }
  stop(){this.stopped=true;if(this.timer)clearTimeout(this.timer);}
}
