'use client';

import { useEffect, useRef } from 'react';

export function LiquidParallaxBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    // 1. Global mouse tracking for CSS variable --mouse-x and --mouse-y
    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth) * 100;
      const y = (e.clientY / window.innerHeight) * 100;
      document.documentElement.style.setProperty('--mouse-x', `${x.toFixed(1)}%`);
      document.documentElement.style.setProperty('--mouse-y', `${y.toFixed(1)}%`);
    };
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    // 2. WebGL Liquid Fluid Ribbon Flow (User's Shader Spec)
    const canvas = canvasRef.current;
    if (!canvas) {
      return () => window.removeEventListener('mousemove', handleMouseMove);
    }

    const gl = canvas.getContext('webgl', { powerPreference: 'high-performance', alpha: true });
    if (!gl) {
      return () => window.removeEventListener('mousemove', handleMouseMove);
    }

    const vsSource = `
      attribute vec2 position;
      varying vec2 vUv;
      void main() {
        vUv = (position + 1.0) * 0.5;
        gl_Position = vec4(position, 0.0, 1.0);
      }
    `;

    const fsSource = `
      precision highp float;
      varying vec2 vUv;
      uniform vec2 uResolution;
      uniform float uTime;
      uniform vec2 uMouse;

      vec3 renderFluid(vec2 uv, float t) {
        vec2 p = uv * 2.0 - 1.0;
        p.x *= uResolution.x / uResolution.y;

        float wave1 = sin(p.x * 1.8 + t * 0.35 + sin(p.y * 2.2 + t * 0.25));
        float wave2 = cos(p.y * 2.0 - t * 0.30 + sin(p.x * 1.9 - t * 0.28));
        float ridge = sin((p.x + p.y) * 2.8 + wave1 * 1.9 - wave2 * 1.5);

        // User palette: deep oceanic navy, cobalt, electric cyan, and soft white foam
        vec3 deepNavy  = vec3(0.008, 0.043, 0.094); // #020b18
        vec3 midCyan   = vec3(0.02, 0.32, 0.65);
        vec3 brightSky = vec3(0.18, 0.62, 0.88);
        vec3 whiteFoam = vec3(0.85, 0.94, 1.0);

        float factor = 0.5 + 0.5 * sin(wave1 * 1.5 + wave2 * 1.2 + ridge * 0.9);
        vec3 col = mix(deepNavy, midCyan, factor * 0.7);

        float highlight = smoothstep(0.52, 0.96, factor);
        col = mix(col, brightSky, highlight * 0.5);

        float crest = smoothstep(0.90, 0.995, sin(ridge * 2.5 + t * 0.8));
        col = mix(col, whiteFoam, crest * 0.45);

        return col;
      }

      void main() {
        vec2 uv = gl_FragCoord.xy / uResolution;
        vec2 mouseDist = (gl_FragCoord.xy - uMouse) / uResolution;
        float ripple = sin(length(mouseDist) * 25.0 - uTime * 3.0) * exp(-length(mouseDist) * 4.0) * 0.015;
        vec3 color = renderFluid(uv + vec2(ripple), uTime);
        gl_FragColor = vec4(color, 1.0);
      }
    `;

    function createShader(glCtx: WebGLRenderingContext, type: number, src: string) {
      const shader = glCtx.createShader(type);
      if (!shader) return null;
      glCtx.shaderSource(shader, src);
      glCtx.compileShader(shader);
      if (!glCtx.getShaderParameter(shader, glCtx.COMPILE_STATUS)) {
        glCtx.deleteShader(shader);
        return null;
      }
      return shader;
    }

    const vs = createShader(gl, gl.VERTEX_SHADER, vsSource);
    const fs = createShader(gl, gl.FRAGMENT_SHADER, fsSource);
    if (!vs || !fs) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);

    const posBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1
    ]), gl.STATIC_DRAW);

    const posLoc = gl.getAttribLocation(program, 'position');
    const uResLoc = gl.getUniformLocation(program, 'uResolution');
    const uTimeLoc = gl.getUniformLocation(program, 'uTime');
    const uMouseLoc = gl.getUniformLocation(program, 'uMouse');

    let mouseGlX = window.innerWidth * 0.5;
    let mouseGlY = window.innerHeight * 0.5;

    const handleGlMouseMove = (e: MouseEvent) => {
      mouseGlX = e.clientX;
      mouseGlY = window.innerHeight - e.clientY;
    };
    window.addEventListener('mousemove', handleGlMouseMove, { passive: true });

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    window.addEventListener('resize', resize, { passive: true });
    resize();

    let animId: number;
    const startTime = performance.now();

    const render = (now: number) => {
      const elapsed = (now - startTime) * 0.001;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);

      gl.useProgram(program);
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

      gl.uniform2f(uResLoc, canvas.width, canvas.height);
      gl.uniform1f(uTimeLoc, elapsed);
      gl.uniform2f(uMouseLoc, mouseGlX * dpr, mouseGlY * dpr);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mousemove', handleGlMouseMove);
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animId);
      gl.deleteProgram(program);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0 bg-[#020b18]" aria-hidden="true">
      <canvas
        ref={canvasRef}
        className="fixed inset-0 w-full h-full pointer-events-none z-0 opacity-80"
        style={{ width: '100vw', height: '100vh' }}
      />
      {/* Depth vignette overlay */}
      <div className="absolute inset-0 bg-radial-[at_50%_30%] from-transparent via-[#020b18]/40 to-[#020b18]/90 pointer-events-none z-1" />
    </div>
  );
}
