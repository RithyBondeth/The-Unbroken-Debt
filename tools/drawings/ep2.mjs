// Episode 2 drawings: hand-inked yantra (យ័ន្ត) cloths for the sealed hall door and
// Sophal's kuti, after the user's reference yantra (2 November 2026): a circular yantra
// with rings of script, eight cartouches and radiating unalom strokes, and a square
// yantra with diagonals, looped corners and a numeral square. Original layouts. Also the
// wat's gilded name board over the gate, and old handprints.
//
// Khmer text: every string is listed in KHMER below for the native-speaker and
// cultural-advisor review (Cultural Guide, section 4). The yantra carry standard Pali
// formulas written in Khmer script, as on real yantra; the gate board carries the wat's
// (fictional) name and year. Keep it to that list.

/** Every Khmer string in these drawings, with its meaning. Review: pending. */
export const KHMER = {
  namoBuddhaya: [
    "នមោពុទ្ធាយ",
    "namo buddhāya: homage to the Buddha (the five-syllable heart formula)",
  ],
  namoSyllables: ["ន មោ ពុ ទ្ធា យ", "the same formula as five separate syllables"],
  maAU: ["ម អ ឧ", "ma a u: the three-syllable heart of the Triple Gem"],
  itipiso: [
    "ឥតិបិសោ ភគវា អរហំ សម្មាសម្ពុទ្ធោ វិជ្ជាចរណសម្បន្នោ សុគតោ លោកវិទូ",
    "itipiso bhagavā arahaṃ sammāsambuddho vijjācaraṇasampanno sugato lokavidū (virtues of the Buddha)",
  ],
  svakkhato: [
    "ស្វាក្ខាតោ ភគវតា ធម្មោ សន្ទិដ្ឋិកោ អកាលិកោ",
    "svākkhāto bhagavatā dhammo sandiṭṭhiko akāliko (virtues of the Dhamma)",
  ],
  supatipanno: [
    "សុប្បដិបន្នោ ភគវតោ សាវកសង្ឃោ",
    "suppaṭipanno bhagavato sāvakasaṅgho (virtues of the Sangha)",
  ],
  triple: ["ពុទ្ធំ ធម្មំ សង្ឃំ", "buddhaṃ dhammaṃ saṅghaṃ: the Triple Gem"],
  arahang: ["អរហំ", "arahaṃ: worthy one"],
  numerals: ["១ ២ ៣ ៤ ៥ ៦ ៧ ៨ ៩", "Khmer numerals one to nine (the numeral square)"],
  // The gate's name board. The wat is fictional; the name and year are for review.
  watName: [
    "វត្តព្រៃស្ងាត់",
    "Wat Prey Sngat: 'pagoda of the silent forest' (the wat's name, on the gate)",
  ],
  watFounded: ["ព.ស. ២៤៥៥", "B.E. 2455 (1912 CE): the year the gate was raised, under the name"],
};

const syll = KHMER.namoSyllables[0].split(" ");
const mau = KHMER.maAU[0].split(" ");
const triple = KHMER.triple[0].split(" ");
const nums = KHMER.numerals[0].split(" ");

/** Shared aged-cotton ground: fibres, foxing, water tide-marks, soot at the top edge. */
const cotton = (seed) => `
  let s=${seed};const r=()=>(s=(s*16807)%2147483647)/2147483647;
  ctx.fillStyle='#c4b48d';ctx.fillRect(0,0,w,h);
  for(let i=0;i<60000;i++){const g=190+r()*40|0;ctx.fillStyle='rgba('+g+','+(g-12)+','+(g-38)+','+(.05+r()*.08)+')';ctx.fillRect(r()*w,r()*h,1+r()*3,1)}
  for(let i=0;i<5000;i++){ctx.strokeStyle='rgba(120,100,70,'+(r()*.08)+')';ctx.lineWidth=.6;const x=r()*w,y=r()*h;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+(r()-.5)*24,y+(r()-.5)*4);ctx.stroke()}
  const stain=(x,y,rad,a)=>{const g=ctx.createRadialGradient(x,y,rad*.2,x,y,rad);g.addColorStop(0,'rgba(140,105,55,'+a*.4+')');g.addColorStop(.85,'rgba(120,85,40,'+a+')');g.addColorStop(1,'rgba(120,85,40,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,rad,0,7);ctx.fill()};
  // Water and smoke stains: irregular blooms built from many small soft blots.
  for(let i=0;i<6;i++){let x=r()*w,y=r()*h;const a=.05+r()*.07;for(let k=0;k<26;k++){stain(x,y,20+r()*70,a);x+=(r()-.5)*90;y+=(r()-.5)*90}}
  for(let i=0;i<140;i++){ctx.fillStyle='rgba(110,70,30,'+(r()*.35)+')';ctx.beginPath();ctx.arc(r()*w,r()*h,1+r()*4,0,7);ctx.fill()}
  const soot=ctx.createLinearGradient(0,0,0,h*.35);soot.addColorStop(0,'rgba(30,24,16,.55)');soot.addColorStop(1,'rgba(30,24,16,0)');ctx.fillStyle=soot;ctx.fillRect(0,0,w,h*.35);
  const edge=ctx.createRadialGradient(w/2,h/2,w*.35,w/2,h/2,w*.75);edge.addColorStop(0,'rgba(60,40,20,0)');edge.addColorStop(1,'rgba(60,40,20,.5)');ctx.fillStyle=edge;ctx.fillRect(0,0,w,h);
`;

/** Ink that has bled a little into the weave and faded unevenly. */
const ink = (colour) => `
  ctx.strokeStyle='${colour}';ctx.fillStyle='${colour}';ctx.shadowColor='${colour}';ctx.shadowBlur=1.5;ctx.lineCap='round';ctx.lineJoin='round';
  const say=(t,x,y,size,rot=0,font='Freehand')=>{ctx.save();ctx.translate(x,y);ctx.rotate(rot);ctx.font=size+'px '+font;ctx.textAlign='center';ctx.textBaseline='middle';ctx.globalAlpha=.78+r()*.2;ctx.fillText(t,0,0);ctx.restore()};
  const unalom=(x,y,a,len,size)=>{ctx.save();ctx.translate(x,y);ctx.rotate(a);ctx.lineWidth=size*.12;ctx.beginPath();
    ctx.moveTo(0,0);for(let t=0;t<1;t+=.02){const k=t*len;ctx.lineTo(k,Math.sin(t*18)*size*.25*(1-t))}ctx.stroke();
    ctx.beginPath();ctx.arc(len+size*.35,0,size*.32,Math.PI,Math.PI*3.4);ctx.stroke();ctx.beginPath();ctx.arc(len+size*1.0,0,size*.08,0,7);ctx.fill();ctx.restore()};
`;

/** Decay that makes the cloth frightening without mocking it: rain has run the ink down
 * the cloth, mildew blooms, a lamp scorched one corner, and an old rust-red handprint
 * has been dragged across the edge, as if someone held on to it. */
const dread = (seed, inkColour) => `
  {let s=${seed};const r=()=>(s=(s*16807)%2147483647)/2147483647;
  // Ink run down the weave: only from the strokes themselves, thin and uneven.
  const src=layer.getContext('2d').getImageData(0,0,w,h).data;
  for(let i=0,n=0;i<40000&&n<420;i++){const x=r()*w|0,y=r()*h|0;if(src[(y*w+x)*4+3]<120)continue;n++;
    let px=x,py=y;const len=15+r()*(r()<.15?260:70),a=.18+r()*.25;
    for(let k=0;k<len;k+=2){ctx.fillStyle='${inkColour}'+Math.round(a*(1-k/len)*255).toString(16).padStart(2,'0');ctx.fillRect(px,py+k,1+(r()<.3),2);px+=(r()-.5)*.8}}
  // Black mildew colonies.
  for(let i=0;i<9;i++){let x=r()*w,y=r()*h;for(let k=0;k<50;k++){ctx.fillStyle='rgba(20,22,14,'+(r()*.2)+')';ctx.beginPath();ctx.arc(x+(r()-.5)*80,y+(r()-.5)*80,1+r()*5,0,7);ctx.fill()}}
  // A scorched corner: soft char built from blots, a darker ragged burn line.
  const left=r()<.5,sx=left?40:w-40,sy=h-40;
  for(let k=0;k<160;k++){const a=r()*Math.PI*2,d=r()*r()*260;const x=sx+Math.cos(a)*d,y=sy+Math.sin(a)*d;const rad=20+r()*60;
    const g=ctx.createRadialGradient(x,y,0,x,y,rad);const dk=1-d/260;g.addColorStop(0,'rgba('+(10+40*(1-dk)|0)+','+(6+22*(1-dk)|0)+',2,'+(.25+.5*dk)+')');g.addColorStop(1,'rgba(40,20,5,0)');ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,rad,0,7);ctx.fill()}
  ctx.strokeStyle='rgba(8,4,1,.7)';ctx.lineWidth=3;ctx.beginPath();for(let a=0;a<=Math.PI*2;a+=.08){const rr=120+Math.sin(a*7)*14+r()*22;ctx.lineTo(sx+Math.cos(a)*rr,sy+Math.sin(a)*rr)}ctx.stroke();
  // An old handprint in rust brown, pressed and dragged down: soft blots, broken skin lines.
  ctx.save();ctx.translate(left?w*.78:w*.22,h*.58);ctx.rotate((left?.25:-.25)+(r()-.5)*.2);
  ctx.scale(1.15,1.15);
  const blot=(x,y,rx,ry,a)=>{for(let k=0;k<rx*ry*1.4;k++){const t=r()*Math.PI*2,q=Math.sqrt(r());ctx.fillStyle='rgba(84,20,9,'+(a*(.25+r()*.5)*(1-q*.5))+')';ctx.fillRect(x+Math.cos(t)*rx*q,y+Math.sin(t)*ry*q,1+r()*3,1+r()*3)}};
  blot(0,0,52,60,.5);blot(-58,18,15,34,.45);
  const fingers=[[-38,-92,12,34],[-12,-112,12,40],[14,-110,12,38],[38,-90,11,30]];
  for(const [fx,fy,rx,ry] of fingers){blot(fx,fy,rx,ry,.5);
    // The drag: the fingers slid down the cloth as the hand fell away.
    for(let k=0;k<180;k++){const t=r();ctx.fillStyle='rgba(88,22,10,'+(.35*(1-t)*r())+')';ctx.fillRect(fx+(r()-.5)*rx*1.6+t*6,fy+ry+t*240,1+r()*2,2+r()*4)}}
  // Palm creases pressed deeper into the weave.
  for(let k=0;k<6;k++){ctx.strokeStyle='rgba(60,12,6,.35)';ctx.lineWidth=1.5;ctx.beginPath();const y=-35+k*14+r()*8;ctx.moveTo(-44,y);ctx.quadraticCurveTo(0,y+(r()-.5)*24,44,y+(r()-.5)*12);ctx.stroke()}
  ctx.restore();
  const dark=ctx.createRadialGradient(w/2,h/2,w*.25,w/2,h/2,w*.72);dark.addColorStop(0,'rgba(0,0,0,0)');dark.addColorStop(1,'rgba(10,6,2,.55)');ctx.fillStyle=dark;ctx.fillRect(0,0,w,h);}
`;

const fade = `
  ctx.globalCompositeOperation='destination-out';ctx.shadowBlur=0;
  for(let i=0;i<900;i++){ctx.fillStyle='rgba(0,0,0,'+(r()*.25)+')';ctx.beginPath();ctx.arc(r()*w,r()*h,2+r()*14,0,7);ctx.fill()}
  ctx.globalCompositeOperation='source-over';
`;

export const drawings = [
  {
    name: "yantra_circle",
    file: "T_ep2_yantra_circle_BC",
    size: [1024, 1024],
    draw: () => `<canvas id="c" width="1024" height="1024"></canvas><script>
    document.fonts.load('40px Freehand').then(()=>{
      const canvas=document.getElementById('c'),ctx=canvas.getContext('2d'),w=1024,h=1024,cx=512,cy=520;
      ${cotton(19321)}
      const layer=document.createElement('canvas');layer.width=w;layer.height=h;
      {const ctx2=ctx;}
      const g=layer.getContext('2d');
      (function(ctx){
        ${ink("#1c1f2c")}
        // Rings: a double circle holding the Buddha's virtues, script set round the path.
        ctx.lineWidth=3;for(const rad of [212,226]){ctx.beginPath();ctx.arc(cx,cy,rad,0,7);ctx.stroke()}
        ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,146,0,7);ctx.stroke();
        // Khmer clusters must stay whole: lay whole words round the ring, each given an
        // arc in proportion to its measured width, the font fitted to the circumference.
        const ring=(text,rad,size)=>{const words=text.split(' ');ctx.font=size+'px Freehand';
          const gap=size*.45,widths=words.map(t=>ctx.measureText(t).width);
          const total=widths.reduce((a,b)=>a+b+gap,0),fit=Math.min(1,Math.PI*2*rad*.97/total),k=size*fit;
          let a=-Math.PI/2;words.forEach((t,i)=>{const arc=(widths[i]*fit)/rad,mid=a+arc/2;
            say(t,cx+Math.cos(mid)*rad,cy+Math.sin(mid)*rad,k,mid+Math.PI/2);a+=arc+(gap*fit)/rad})};
        ring(${JSON.stringify(KHMER.itipiso[0])},188,30);
        ring(${JSON.stringify(KHMER.svakkhato[0] + " " + KHMER.supatipanno[0])},124,22);
        say(${JSON.stringify(KHMER.namoBuddhaya[0])},cx,cy-20,34);
        say(${JSON.stringify(KHMER.maAU[0])},cx,cy+26,32);
        // Eight cartouches round the ring, each with two lines and a circled syllable outside.
        for(let i=0;i<8;i++){
          const a=i*Math.PI/4-Math.PI/2,x=cx+Math.cos(a)*292,y=cy+Math.sin(a)*292;
          ctx.save();ctx.translate(x,y);ctx.rotate(a+Math.PI/2);ctx.lineWidth=2.5;
          ctx.beginPath();ctx.roundRect(-62,-46,124,92,26);ctx.stroke();
          ctx.beginPath();ctx.moveTo(-52,2);ctx.lineTo(52,2);ctx.stroke();
          ctx.restore();
          say(${JSON.stringify(triple)}[i%3],x+Math.cos(a)*22,y+Math.sin(a)*22,24,a+Math.PI/2);
          say(${JSON.stringify(syll)}[i%5],x-Math.cos(a)*22,y-Math.sin(a)*22,24,a+Math.PI/2);
          const ox=cx+Math.cos(a)*362,oy=cy+Math.sin(a)*362;
          ctx.lineWidth=2;ctx.beginPath();ctx.arc(ox,oy,19,0,7);ctx.stroke();
          say(${JSON.stringify(mau)}[i%3],ox,oy,24,a+Math.PI/2);
          // Radiating strokes between the cartouches, ending in unalom spirals and syllables.
          const b=a+Math.PI/8;
          ctx.lineWidth=2.5;ctx.beginPath();ctx.moveTo(cx+Math.cos(b)*232,cy+Math.sin(b)*232);ctx.lineTo(cx+Math.cos(b)*400,cy+Math.sin(b)*400);ctx.stroke();
          unalom(cx+Math.cos(b)*400,cy+Math.sin(b)*400,b,40,26);
          say(${JSON.stringify(nums)}[i],cx+Math.cos(b+.13)*440,cy+Math.sin(b+.13)*440,26,b+Math.PI/2);
          say(${JSON.stringify(KHMER.arahang[0])},cx+Math.cos(b-.12)*470,cy+Math.sin(b-.12)*470,24,b+Math.PI/2);
        }
      })(g);
      // Bake a worn ink layer onto the cotton.
      (function(){const ctx=g;let s=777;const r=()=>(s=(s*16807)%2147483647)/2147483647;${fade}})();
      ctx.globalAlpha=.9;ctx.drawImage(layer,0,0);ctx.globalAlpha=1;
      ${dread(5113, "#1c1f2c")}
    });
    </script>`,
  },
  {
    name: "yantra_square",
    file: "T_ep2_yantra_square_BC",
    size: [1024, 1024],
    draw: () => `<canvas id="c" width="1024" height="1024"></canvas><script>
    document.fonts.load('40px Freehand').then(()=>{
      const canvas=document.getElementById('c'),ctx=canvas.getContext('2d'),w=1024,h=1024;
      ${cotton(19322)}
      const layer=document.createElement('canvas');layer.width=w;layer.height=h;const g=layer.getContext('2d');
      (function(ctx){
        ${ink("#2a3474")}
        const x0=262,y0=300,x1=762,y1=800,mx=512,my=550;
        ctx.lineWidth=3.5;ctx.strokeRect(x0,y0,x1-x0,y1-y0);
        ctx.lineWidth=2.5;
        for(const [a,b,c,d] of [[x0,y0,x1,y1],[x1,y0,x0,y1],[mx,y0,x1,my],[x1,my,mx,y1],[mx,y1,x0,my],[x0,my,mx,y0]]){ctx.beginPath();ctx.moveTo(a,b);ctx.lineTo(c,d);ctx.stroke()}
        // Open loops at the corners and the middle of each side.
        for(const [x,y,ax,ay] of [[x0,y0,-1,-1],[x1,y0,1,-1],[x0,y1,-1,1],[x1,y1,1,1],[mx,y0,0,-1],[mx,y1,0,1],[x0,my,-1,0],[x1,my,1,0]]){
          ctx.beginPath();ctx.arc(x+ax*20,y+ay*20,20,0,7);ctx.stroke()}
        // A numeral square in the outer triangles, the heart syllables within.
        // Centroids of the eight outer triangles between the sides, diagonals and diamond.
        const cells=[[x0+125,y0+44],[x1-125,y0+44],[x1-44,y0+125],[x1-44,y1-125],[x1-125,y1-44],[x0+125,y1-44],[x0+44,y1-125],[x0+44,y0+125]];
        const square=[${JSON.stringify(nums)}[7],${JSON.stringify(nums)}[0],${JSON.stringify(nums)}[5],${JSON.stringify(nums)}[6],${JSON.stringify(nums)}[1],${JSON.stringify(nums)}[8],${JSON.stringify(nums)}[3],${JSON.stringify(nums)}[2]];
        cells.forEach(([x,y],i)=>say(square[i],x,y,34));
        [[mx,y0+135],[x1-135,my],[mx,y1-135],[x0+135,my]].forEach(([x,y],i)=>say(${JSON.stringify(syll)}[i+1],x,y,34));
        // Above: the unalom crown and the homage; below: the virtues; columns at the sides.
        unalom(mx,140,-Math.PI/2,40,30);
        say(${JSON.stringify(KHMER.namoBuddhaya[0])},mx,222,58);
        say(${JSON.stringify(KHMER.itipiso[0].split(" ").slice(0, 3).join(" "))},mx,884,46);
        say(${JSON.stringify(KHMER.triple[0])},mx,950,36);
        ${JSON.stringify(syll)}.forEach((t,i)=>{say(t,150,360+i*84,38);say(${JSON.stringify(mau)}[i%3],876,380+i*84,38)});
        for(const [x,side] of [[150,1],[876,-1]]){unalom(x,330,-Math.PI/2,26,22)}
      })(g);
      (function(){const ctx=g;let s=778;const r=()=>(s=(s*16807)%2147483647)/2147483647;${fade}})();
      ctx.globalAlpha=.88;ctx.drawImage(layer,0,0);ctx.globalAlpha=1;
      ${dread(5114, "#2a3474")}
    });
    </script>`,
  },
  {
    // Old rust-red handprints on plaster: pressed, dragged down, smeared sideways.
    name: "handprints",
    file: "T_ep2_handprints_BC",
    size: [1024, 512],
    alpha: true,
    draw: () => `<canvas id="c" width="1024" height="512"></canvas><script>
      const ctx=document.getElementById('c').getContext('2d'),w=1024,h=512;let s=40433;const r=()=>(s=(s*16807)%2147483647)/2147483647;
      const print=(cx,cy,scale,rot,drag,alpha)=>{ctx.save();ctx.translate(cx,cy);ctx.rotate(rot);ctx.scale(scale,scale);
        // A human hand: a squarish palm, four long joined fingers, a thumb angled from the heel.
        const hand=new Path2D();hand.roundRect(-46,-50,92,104,[18,18,30,30]);
        for(const [fx,len,wd] of [[-33,78,21],[-11,94,22],[12,88,21],[33,68,19]])hand.roundRect(fx-wd/2,-50-len,wd,len+14,10);
        const thumb=new Path2D();thumb.roundRect(-11,-34,22,74,11);
        const m=new DOMMatrix().translate(-44,18).rotate(-48);hand.addPath(thumb,m);
        ctx.save();ctx.clip(hand);
        for(let k=0;k<9000;k++){const x=-110+r()*200,y=-160+r()*220;ctx.fillStyle='rgba(78,14,6,'+(alpha*(.25+r()*.6))+')';ctx.fillRect(x,y,1+r()*3,1+r()*3)}
        // Skin creases and finger joints left pale where the hand pressed least.
        for(let k=0;k<7;k++){ctx.strokeStyle='rgba(255,255,255,0)';ctx.globalCompositeOperation='destination-out';ctx.strokeStyle='rgba(0,0,0,.35)';ctx.lineWidth=1.6;ctx.beginPath();const y=-30+k*12+r()*6;ctx.moveTo(-44,y);ctx.quadraticCurveTo(0,y+(r()-.5)*20,44,y+(r()-.5)*10);ctx.stroke()}
        for(const [fx,len] of [[-33,78],[-11,94],[12,88],[33,68]])for(const j of [.33,.66]){ctx.beginPath();ctx.moveTo(fx-10,-50-len*j);ctx.lineTo(fx+10,-50-len*j);ctx.stroke()}
        ctx.globalCompositeOperation='source-over';ctx.restore();
        // The drag: the fingers slid down as the hand fell away.
        for(const [fx] of [[-33],[-11],[12],[33]])for(let k=0;k<300*drag;k++){const t=r();ctx.fillStyle='rgba(78,14,6,'+(.4*(1-t)*r()*alpha)+')';ctx.fillRect(fx+(r()-.5)*18+t*6,54+t*260*drag,1+r()*2,2+r()*5)}
        ctx.restore()};
      print(150,230,1.1,-.15,1,1);print(420,200,1.0,.25,.4,.8);print(640,260,1.15,-.05,1.2,.9);print(880,210,.9,.4,.2,.6);
    </script>`,
  },
  {
    // The wat's name board over the gate: gilded letters raised on red lacquer, as Khmer gate
    // boards are, now flaking to the plaster, streaked with damp, cracked through, and dragged
    // across by a rust-red hand.
    name: "gate_name",
    file: "T_ep2_gate_name_BC",
    size: [2048, 352],
    draw: () => `<canvas id="c" width="2048" height="352"></canvas><script>
    document.fonts.load('150px Preahvihear').then(()=>{
      const ctx=document.getElementById('c').getContext('2d'),w=2048,h=352;let s=27455;const r=()=>(s=(s*16807)%2147483647)/2147483647;
      // Old red lacquer over lime plaster: brushed grain, darker where the damp sits.
      ctx.fillStyle='#3a0c08';ctx.fillRect(0,0,w,h);
      for(let i=0;i<26000;i++){const g=r();ctx.fillStyle='rgba('+(60+g*40|0)+','+(12+g*10|0)+','+(8+g*6|0)+','+(.08+r()*.12)+')';ctx.fillRect(r()*w,r()*h,4+r()*40,1+r()*2)}
      // Gilded frame: a raised double border with lotus buds at the corners.
      const gold=(y0,y1)=>{const g=ctx.createLinearGradient(0,y0,0,y1);g.addColorStop(0,'#b8954a');g.addColorStop(.45,'#7d5c22');g.addColorStop(1,'#43300f');return g};
      ctx.lineJoin='round';
      for(const [m,wd] of [[14,10],[34,4]]){ctx.strokeStyle=gold(m,h-m);ctx.lineWidth=wd;ctx.shadowColor='rgba(0,0,0,.7)';ctx.shadowBlur=6;ctx.shadowOffsetY=3;
        ctx.beginPath();ctx.roundRect(m,m,w-2*m,h-2*m,26);ctx.stroke()}
      for(const [x,y] of [[60,60],[w-60,60],[60,h-60],[w-60,h-60]]){ctx.fillStyle=gold(y-22,y+22);ctx.beginPath();ctx.ellipse(x,y,14,22,0,0,7);ctx.fill()}
      // The name, then the year, in raised gold: a dark undercut below, light catching the top.
      const raised=(t,y,size)=>{ctx.font=size+'px Preahvihear';ctx.textAlign='center';ctx.textBaseline='middle';
        ctx.shadowColor='rgba(10,2,0,.85)';ctx.shadowBlur=8;ctx.shadowOffsetX=0;ctx.shadowOffsetY=6;ctx.fillStyle=gold(y-size*.6,y+size*.6);ctx.fillText(t,w/2,y);
        ctx.shadowColor='transparent';ctx.fillStyle='rgba(255,236,170,.18)';ctx.fillText(t,w/2,y-2)};
      raised(${JSON.stringify(KHMER.watName[0])},150,150);
      raised(${JSON.stringify(KHMER.watFounded[0])},272,54);
      ctx.shadowColor='transparent';
      // Gold and lacquer both flake back to grey plaster: small scabs in clusters, worst along
      // the bottom edge and round the crack, their edges dark with dirt.
      const scab=(x,y,rad)=>{ctx.beginPath();for(let k=0;k<9;k++){const a=k/9*Math.PI*2,q=rad*(.45+r()*.8);k?ctx.lineTo(x+Math.cos(a)*q,y+Math.sin(a)*q*.7):ctx.moveTo(x+Math.cos(a)*q,y+Math.sin(a)*q*.7)}ctx.closePath();
        ctx.fillStyle='rgba('+(78+r()*20|0)+','+(74+r()*16|0)+','+(64+r()*12|0)+',.85)';ctx.fill();ctx.strokeStyle='rgba(20,10,6,.6)';ctx.lineWidth=1.5;ctx.stroke()};
      for(let c=0;c<34;c++){const cx=c<8?1100+r()*260:r()*w,cy=c<8?r()*h:h*(.55+r()*.45);for(let k=0;k<4+r()*10;k++)scab(cx+(r()-.5)*90,cy+(r()-.5)*40,2+r()*9)}
      // Grime over everything: damp running down from the cornice, mould blooming in it,
      // soot along the top, and the board dulled toward its ends.
      for(let i=0;i<90;i++){const x=r()*w,len=60+r()*300;const g=ctx.createLinearGradient(0,0,0,len);g.addColorStop(0,'rgba(10,8,4,.6)');g.addColorStop(1,'rgba(10,8,4,0)');ctx.fillStyle=g;ctx.fillRect(x,0,2+r()*8,len)}
      for(let i=0;i<50;i++){const x=r()*w,y=r()*h*.6;for(let k=0;k<30;k++){ctx.fillStyle='rgba(14,18,8,'+(r()*.28)+')';ctx.beginPath();ctx.arc(x+(r()-.5)*100,y+(r()-.5)*44,2+r()*10,0,7);ctx.fill()}}
      const soot=ctx.createLinearGradient(0,0,0,h*.4);soot.addColorStop(0,'rgba(6,4,2,.6)');soot.addColorStop(1,'rgba(6,4,2,0)');ctx.fillStyle=soot;ctx.fillRect(0,0,w,h*.4);
      const dull=ctx.createLinearGradient(0,0,w,0);dull.addColorStop(0,'rgba(8,4,2,.55)');dull.addColorStop(.3,'rgba(8,4,2,.15)');dull.addColorStop(.7,'rgba(8,4,2,.15)');dull.addColorStop(1,'rgba(8,4,2,.55)');ctx.fillStyle=dull;ctx.fillRect(0,0,w,h);
      // A crack right through the board, the plaster dark in it.
      ctx.strokeStyle='rgba(6,3,1,.95)';ctx.lineWidth=5;ctx.beginPath();let x=1180,y=0;ctx.moveTo(x,y);
      while(y<h){x+=(r()-.45)*60;y+=14+r()*26;ctx.lineTo(x,y)}ctx.stroke();
      ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(1205,120);ctx.lineTo(1290,150);ctx.lineTo(1330,138);ctx.lineTo(1420,190);ctx.stroke();
      // A hand pressed at the left end and dragged along under the name: rust-brown, the
      // palm heavy, four fingers trailing off thinner as the smear runs out.
      ctx.save();ctx.translate(250,250);ctx.rotate(-.08);
      for(let k=0;k<5000;k++){const a=r()*Math.PI*2,q=Math.sqrt(r());ctx.fillStyle='rgba(70,12,6,'+(.15+r()*.45)+')';ctx.fillRect(Math.cos(a)*q*44,Math.sin(a)*q*52,1+r()*3,1+r()*3)}
      for(let f=0;f<4;f++){const fy=-36+f*24;for(let k=0;k<2400;k++){const t=Math.pow(r(),.7);ctx.fillStyle='rgba(70,12,6,'+((1-t)*(.2+r()*.5))+')';ctx.fillRect(30+t*620,fy+(r()-.5)*(12-8*t)+t*24,1+r()*3,1+r()*2)}}
      ctx.restore();
    });
    </script>`,
  },
];
