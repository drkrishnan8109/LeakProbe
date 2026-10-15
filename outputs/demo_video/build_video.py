"""Build a five-minute narrated walkthrough from the local demo artifacts."""
import json, subprocess, textwrap, csv, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent.parent
W,H = 1920,1080
BG='#081521'; PANEL='#102536'; WHITE='#edf5fa'; MUTED='#9bb4c5'; TEAL='#48debd'; BLUE='#65baff'; GOLD='#ffcc72'
def font(n,bold=False):
    return ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial'+(' Bold' if bold else '')+'.ttf',n)
def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
def duration(path):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(path)]))
TRACE=json.loads((ROOT/'outputs/scripted_trace.json').read_text())
BEFORE=TRACE[3]['result']['ranking']; AFTER=TRACE[-1]['result']['ranking']
READING=TRACE[5]['result']['pressure_head_m']
SCENES=[
('LeakProbe','Choose the next measurement', 'intro',
 'Water network sensors can reveal a problem without showing exactly where it is. Leak Probe explores a practical response: compare possible explanations, identify the most useful measurement, and update the result. This five minute walkthrough uses the actual local demo output. Every reading is synthetic, and the investigation sequence is scripted.'),
('01 / The problem','An upstream signal can hide the location','network',
 'The example has one water supply and two matching branches. A flow sensor and a pressure sensor sit upstream of the split. Either branch can develop a leak. Because the branches are symmetric, these upstream sensors produce the same modeled response for leak A and leak B. More upstream readings cannot resolve that tie.'),
('02 / The model','Three explanations, one hydraulic simulator','model',
 'The demo uses W N T R to simulate normal operation, a leak on branch A, and a leak on branch B. Supply head is forty two meters, and each end junction requests five liters per second. A sixteen millimeter leak opens halfway along one branch at two twenty. The simulator computes the resulting flow and pressure.'),
('03 / Run it locally','Python 3.12. No inference API required.','terminal',
 'The local walkthrough runs with Python three point twelve. Create a virtual environment, activate it, install the requirements, and run the demo script. That command generates the prediction files and observations, then executes the investigation tools. This run completed successfully. It uses the local simulator, so the walkthrough needs no model credentials or paid inference requests.'),
('04 / Observe the change','Flow rises after 02:20','chart',
 'The observation file contains ten readings at five minute intervals, from two o clock to two forty five. The synthetic upstream flow rises from about ten to fourteen point one five liters per second after the leak begins. Pressure also falls slightly. Small reproducible noise is added to observations. These signals support a leak scenario, but leave its branch unresolved.'),
('05 / Compare hypotheses','A and B fit equally well','before',
 'The comparison tool aligns the timestamps and scores the flow and pressure residuals against each scenario. Before a branch measurement, both leak scenarios score zero point one two three seven. Normal operation scores eleven point four two seven zero. Lower normalized error means a better fit. These scores are neither probabilities nor confidence levels, and only three fixed explanations are compared.'),
('06 / Check the context','Scheduled work was cancelled','operations',
 'The tools also expose fictional maintenance records. One record schedules flushing on branch B. A later linked record says that flushing was cancelled and the crew reassigned. That context matters when interpreting an apparent leak signal. However, this starter simulator does not model flushing or sensor bias, and the numeric ranking does not automatically interpret the maintenance notes.'),
('07 / Plan the next measurement','MA fits the 20-minute budget','planner',
 'The planner compares the predicted branch pressures for the two leak scenarios. Both measurement points offer about one point six three meters of separation. But visiting M A takes fifteen minutes, while M B takes thirty. With twenty minutes available, only M A is feasible. The tool chooses pressure separation per minute using a simple demonstration heuristic.'),
('08 / Reveal branch evidence','MA reads 37.809 m of pressure head','measurement',
 'The collection tool reveals the synthetic M A reading: thirty seven point eight zero nine meters of pressure head. Leak A predicts about thirty seven point seven seven nine meters at that location. Leak B predicts thirty nine point four one one. The visit consumes fifteen minutes, leaving five. This fixture assumes the final simulated hydraulic state stays steady until collection.'),
('09 / Update the result','Branch A now fits best','after',
 'With the branch reading included, the tool compares the scenarios again. Leak A now scores zero point one two five one, while leak B scores one point seven five two two. Normal operation remains a poor fit at eleven point three seven nine nine. Branch A best explains this synthetic evidence among the modeled candidates. That result does not confirm a real field leak.'),
('10 / Inspect the evidence','Every tool result is saved','trace',
 'The full tool sequence is saved in the scripted trace file. It includes the observations, network, maintenance notes, rankings, recommendation, and collected reading. Prediction files expose the underlying simulation results. This evidence trail is reviewable: you can see exactly why the result changes when a branch reading distinguishes two explanations that previously matched the upstream sensors equally well.'),
('11 / What this demonstrates','Compare. Measure. Update.','closing',
 'Leak Probe demonstrates how a limited measurement budget can guide an investigation. The next extension is an optional language model that chooses tools through the same interface. That live path is separate and was not used here. Before field use, the system would need calibrated uncertainty, alternative scenarios, and validation against independent observations. Today, this is a reproducible educational prototype.'),
]

def base(i):
    im=Image.new('RGB',(W,H),BG); d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,8),fill=TEAL)
    d.text((100,50),'LEAKPROBE  /  LOCAL DEMO',font=font(25,True),fill=TEAL)
    d.text((1690,50),f'{i+1:02d} / 12',font=font(25),fill=MUTED)
    d.text((100,118),SCENES[i][0],font=font(34),fill=MUTED)
    d.text((100,177),SCENES[i][1],font=font(61,True),fill=WHITE)
    d.rounded_rectangle((90,282,1830,857),radius=25,fill=PANEL)
    d.text((100,1015),'Synthetic data  |  Scripted investigation  |  Actual local run',font=font(23),fill=MUTED)
    for j in range(12):
        d.rounded_rectangle((1370+j*37,1023,1398+j*37,1030),radius=3,fill=TEAL if j<=i else '#284355')
    return im,d
def text(d,xy,s,n=34,color=WHITE,bold=False): d.text(xy,s,font=font(n,bold),fill=color)
def card(d,x,y,w,title,value,note,color=TEAL):
    d.rounded_rectangle((x,y,x+w,y+260),radius=18,fill='#173447')
    text(d,(x+30,y+25),title,30,MUTED)
    text(d,(x+30,y+82),value,62,color,True)
    for k,line in enumerate(textwrap.wrap(note,width=int(w/19))): text(d,(x+30,y+178+k*35),line,27)
def network(d):
    pts=[(410,390),(760,390),(1100,550),(1510,390),(1510,730)]
    d.line([pts[0],pts[1],pts[2]],fill=BLUE,width=12)
    d.line([pts[2],pts[3]],fill=TEAL,width=12); d.line([pts[2],pts[4]],fill=GOLD,width=12)
    for x,y in pts: d.ellipse((x-22,y-22,x+22,y+22),fill=WHITE)
    for x,y,label in [(300,320,'Supply R0'),(680,320,'F01 flow'),(880,620,'P01 pressure'),(1440,320,'MA / branch A'),(1440,780,'MB / branch B')]: text(d,(x,y),label,30)
    text(d,(160,735),'Identical branches. Shared upstream sensors.',35,MUTED)
def rankings(d,rows):
    labels={'leak_A':'Leak A','leak_B':'Leak B','normal':'Normal'}
    for j,r in enumerate(rows):
        y=345+j*148; c=TEAL if r['scenario']=='leak_A' else BLUE if r['scenario']=='leak_B' else MUTED
        text(d,(140,y),labels[r['scenario']],37,c,True)
        score=r['normalized_rmse']; length=max(18,1000*score/12)
        d.rounded_rectangle((420,y,420+length,y+47),radius=10,fill=c)
        text(d,(1500,y),f'{score:.4f}',43,c,True)
    text(d,(140,790),'Normalized RMSE  /  lower is better fit  /  not confidence',29,MUTED)
def content(i):
    im,d=base(i); kind=SCENES[i][2]
    if kind=='intro':
        text(d,(150,340),'Where should we measure next?',64,WHITE,True)
        for x,a,b,c in [(150,'COMPARE','3 scenarios','Normal, leak A, leak B'),(720,'MEASURE','15 minutes','One feasible branch visit'),(1290,'UPDATE','New evidence','A previously tied result')]: card(d,x,475,480,a,b,c)
    elif kind=='network': network(d)
    elif kind=='model':
        card(d,140,335,490,'SUPPLY HEAD','42 m','Fixed reservoir head')
        card(d,715,335,490,'JUNCTION DEMAND','5 L/s','Each branch end requests 5 L/s',BLUE)
        card(d,1290,335,490,'LEAK OPENING','16 mm','Mid-pipe leak begins 02:20',GOLD)
        text(d,(140,670),'WNTR hydraulic simulation',45,WHITE,True)
        text(d,(140,738),'Normal operation  /  leak A  /  leak B',37,MUTED)
    elif kind=='terminal':
        commands=['$ python3.12 -m venv .venv','$ source .venv/bin/activate','$ python -m pip install -r requirements.txt','$ python run_demo.py']
        for j,s in enumerate(commands): text(d,(140,330+j*63),s,34,TEAL)
        log=(OUT/'demo_run.txt').read_text()
        excerpt=[s for s in log.splitlines() if s.startswith('Recommended') or s.startswith('Synthetic reading')]
        for j,s in enumerate(['SCRIPTED LOCAL DEMO - no LLM or API calls']+excerpt): text(d,(140,625+j*57),s,34,WHITE)
        text(d,(140,805),'Commands and output from the successful local run',25,MUTED)
    elif kind=='chart':
        readings=TRACE[0]['result']['readings']; x0,x1,y0,y1=220,1680,350,730
        for v in [10,12,14]:
            y=y1-(v-9)/6*(y1-y0); d.line((x0,y,x1,y),fill='#284355',width=2); text(d,(125,y-20),str(v),27,MUTED)
        points=[(x0+j/9*(x1-x0),y1-(r['F01_flow_lps']-9)/6*(y1-y0)) for j,r in enumerate(readings)]
        d.line(points,fill=TEAL,width=7)
        for x,y in points: d.ellipse((x-9,y-9,x+9,y+9),fill=TEAL)
        for j,label in [(0,'02:00'),(4,'02:20'),(9,'02:45')]: text(d,(x0+j/9*(x1-x0)-45,750),label,28,MUTED)
        text(d,(140,305),'F01 flow (L/s)  /  synthetic observations',28,MUTED)
        text(d,(970,365),'Leak starts',31,GOLD)
        text(d,(140,811),'10 readings  /  5-minute intervals  /  reproducible noise',26,MUTED)
    elif kind=='before': rankings(d,BEFORE)
    elif kind=='after': rankings(d,AFTER)
    elif kind=='operations':
        text(d,(150,345),'OP01  /  Branch B',31,MUTED)
        text(d,(150,405),'Flushing scheduled: 02:15 to 03:00 UTC',44,WHITE,True)
        text(d,(150,525),'OP03  /  linked cancellation at 01:55 UTC',31,TEAL)
        text(d,(150,585),'Flushing cancelled. Crew reassigned.',44,TEAL,True)
        text(d,(150,745),'Context is available to inspect; flushing is not a simulated scenario.',30,MUTED)
    elif kind=='planner':
        card(d,140,335,490,'REMAINING BUDGET','20 min','Visit must fit the budget')
        card(d,715,335,490,'MA / FEASIBLE','15 min','10 min setup + 5 min measurement')
        card(d,1290,335,490,'MB / NOT FEASIBLE','30 min','25 min setup + 5 min measurement',GOLD)
        text(d,(140,665),'A vs B pressure separation: 1.632 m at either point',40,WHITE,True)
        text(d,(140,745),'Selection heuristic: pressure separation per minute',32,MUTED)
    elif kind=='measurement':
        card(d,140,335,490,'MA / OBSERVED',f'{READING:.3f} m','Synthetic fixture reading')
        card(d,715,335,490,'LEAK A / PREDICTED',f"{BEFORE[0]['predicted_final']['MA_pressure_m']:.3f} m",'Pressure head at MA',BLUE)
        card(d,1290,335,490,'LEAK B / PREDICTED',f"{BEFORE[1]['predicted_final']['MA_pressure_m']:.3f} m",'Pressure head at MA',GOLD)
        text(d,(140,665),'15 minutes consumed. 5 minutes remain.',43,WHITE,True)
        text(d,(140,745),'Steady hydraulic conditions after leak onset are assumed.',31,MUTED)
    elif kind=='trace':
        seq=['get_observations + get_network + get_operation_records','compare_hypotheses -> initial tie','recommend_measurement -> MA','collect_demo_measurement -> 37.809 m','compare_hypotheses -> leak A best fit']
        for j,s in enumerate(seq): text(d,(140,330+j*76),f'{j+1}.  {s}',32,TEAL if j==4 else WHITE)
        text(d,(140,760),'outputs/scripted_trace.json  +  data/*.csv',35,BLUE,True)
    elif kind=='closing':
        text(d,(150,340),'A reproducible investigation loop',60,WHITE,True)
        text(d,(150,450),'Compare hypotheses -> choose evidence -> update the fit',39,TEAL)
        text(d,(150,560),'Optional next step: LLM tool calling through Nebius',35,WHITE)
        text(d,(150,645),'Future work: independent data, more scenarios, calibrated uncertainty',32,MUTED)
        text(d,(150,740),'Educational prototype. Synthetic evidence. No field confirmation.',32,GOLD)
    return im

def timestamp(t):
    ms=round(t*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

def prepare(i):
    folder=OUT/f'scene_{i+1:02}'; folder.mkdir(exist_ok=True)
    sentences=SCENES[i][3].split('. ')
    sentences=[s if s.endswith('.') else s+'.' for s in sentences]
    if (folder/'clip.mp4').exists() and all((folder/f'voice_{j:02}.txt').exists() and (folder/f'voice_{j:02}.txt').read_text()==s for j,s in enumerate(sentences)):
        cursor=0.6; cues=[]
        for j,s in enumerate(sentences):
            dur=duration(folder/f'voice_{j:02}.aiff')
            cues.append((i*25+cursor,i*25+cursor+dur,s)); cursor+=dur
        if cursor>24.65: raise RuntimeError('Cached scene exceeds duration')
        print(f'Scene {i+1:02}/12 verified from cache',flush=True)
        return cues
    images=[]; audios=[]; cues=[]; cursor=0.6
    backdrop=content(i); backdrop.save(folder/'clean.png')
    for j,s in enumerate(sentences):
        txt=folder/f'voice_{j:02}.txt'; txt.write_text(s)
        audio=folder/f'voice_{j:02}.aiff'
        run(['say','-v','Samantha','-r','165','-f',str(txt),'-o',str(audio)])
        dur=duration(audio)
        frame=backdrop.copy(); d=ImageDraw.Draw(frame)
        lines=textwrap.wrap(s,width=96)
        for k,line in enumerate(lines):
            box=d.textbbox((0,0),line,font=font(32)); x=(W-(box[2]-box[0]))/2
            text(d,(x,900+k*43),line,32,WHITE)
        path=folder/f'caption_{j:02}.png'; frame.save(path)
        images.append((path,dur)); audios.append(audio)
        cues.append((i*25+cursor,i*25+cursor+dur,s)); cursor+=dur
    if cursor>24.65: raise RuntimeError(f'Scene {i+1} narration too long: {cursor:.2f}s')
    # Hold the opening caption for 0.6 seconds before speech; finish on the clean visual.
    entries=[(images[0][0],0.6)]+images+[(folder/'clean.png',25-cursor)]
    image_list=folder/'images.txt'
    image_list.write_text(''.join(f"file '{p}'\nduration {t:.6f}\n" for p,t in entries)+f"file '{folder/'clean.png'}'\n")
    audio_list=folder/'audio.txt'; audio_list.write_text(''.join(f"file '{p}'\n" for p in audios))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(audio_list),'-c:a','pcm_s16le',str(folder/'voice.wav')])
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(image_list),'-i',str(folder/'voice.wav'),'-vf','fps=24,fade=t=in:st=0:d=0.3,fade=t=out:st=24.7:d=0.3','-af','adelay=600:all=1,apad,loudnorm=I=-16:TP=-1.5:LRA=11','-t','25','-c:v','libx264','-preset','fast','-crf','21','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',str(folder/'clip.mp4')])
    print(f'Scene {i+1:02}/12 ready: voice {cursor-0.6:.1f}s',flush=True)
    return cues

if __name__=='__main__':
    (OUT/'narration.txt').write_text('\n\n'.join(f'{i*25//60:02}:{i*25%60:02} | {a}\n{b}\n\n{s}' for i,(a,b,k,s) in enumerate(SCENES)))
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(prepare,range(12)))
    cues=[c for scene in results for c in scene]
    (OUT/'leakprobe-demo.srt').write_text('\n\n'.join(f'{j+1}\n{timestamp(a)} --> {timestamp(b)}\n{textwrap.fill(s,80)}' for j,(a,b,s) in enumerate(cues))+'\n')
    clips=OUT/'clips.txt'; clips.write_text(''.join(f"file '{OUT/f'scene_{i+1:02}'/'clip.mp4'}'\n" for i in range(12)))
    run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(clips),'-i',str(OUT/'leakprobe-demo.srt'),'-map','0:v','-map','0:a','-map','1:0','-c:v','copy','-c:a','copy','-c:s','mov_text','-metadata','title=LeakProbe | Five-minute narrated demo','-metadata:s:s:0','language=eng','-movflags','+faststart',str(OUT/'leakprobe-demo-5min.mp4')])
    previews=[Image.open(OUT/f'scene_{i+1:02}'/'clean.png').resize((640,360)) for i in range(12)]
    montage=Image.new('RGB',(1920,1440))
    for i,im in enumerate(previews): montage.paste(im,((i%3)*640,(i//3)*360))
    montage.save(OUT/'storyboard.jpg',quality=92)
    print('Finished:',OUT/'leakprobe-demo-5min.mp4',flush=True)
