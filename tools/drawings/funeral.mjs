// Exact Khmer lettering is shaped by the same browser/font pipeline as the
// studio prints. Source text and its meaning live in ep1.mjs's KHMER inventory.
export function funeralTributeTextures(words) {
  return [
    {
      name: "funeral_tribute_banner",
      file: "T_ep1_funeral_tribute_banner_BC",
      size: [2048, 384],
      draw: () => `<canvas id="tribute" width="2048" height="384"></canvas><script>
      document.fonts.load('172px Preahvihear').then(() => {
        const canvas=document.getElementById('tribute'),ctx=canvas.getContext('2d');
        const w=canvas.width,h=canvas.height;
        ctx.fillStyle='#151514';ctx.fillRect(0,0,w,h);
        for(let y=0;y<h;y+=3){ctx.fillStyle=y%6?'#171716':'#131312';ctx.fillRect(0,y,w,1)}
        ctx.strokeStyle='#4a4941';ctx.lineWidth=2;
        ctx.setLineDash([7,8]);
        for(const y of [17,h-17]){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
        const text=${JSON.stringify(words.funeralCondolence[0])};
        let size=172;ctx.font=size+'px Preahvihear';
        size*=Math.min(1,(w-180)/ctx.measureText(text).width);
        ctx.font=size+'px Preahvihear';ctx.textAlign='center';ctx.textBaseline='alphabetic';
        const m=ctx.measureText(text);
        ctx.fillStyle='#e3dfd2';
        ctx.fillText(text,w/2,(h+m.actualBoundingBoxAscent-m.actualBoundingBoxDescent)/2);
      });
    </script>`,
    },
  ];
}
