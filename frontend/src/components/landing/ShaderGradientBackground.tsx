'use client';
import { ShaderGradientCanvas, ShaderGradient } from 'shadergradient';

export function ShaderGradientBackground() {
  return (
    <div className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none z-0">
      <ShaderGradientCanvas
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
        pixelDensity={1}
        fov={45}
      >
        <ShaderGradient
          control="props"
          animate="on"
          type="waterPlane"
          color1="#87a1ff"
          color2="#cdcdd1"
          color3="#fafdff"
          brightness={1}
          cAzimuthAngle={170}
          cDistance={4.4}
          cPolarAngle={70}
          cameraZoom={1}
          envPreset="city"
          grain="off"
          lightType="3d"
          positionX={0}
          positionY={0.9}
          positionZ={-0.3}
          rotationX={45}
          rotationY={0}
          rotationZ={0}
          shader="defaults"
          uAmplitude={0}
          uDensity={1.2}
          uFrequency={0}
          uSpeed={0.2}
          uStrength={3.4}
          uTime={0}
          wireframe={false}
        />
      </ShaderGradientCanvas>
      {/* Soft gradient fade into page content */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/20 via-transparent to-[#F8F9FB] z-10 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#F8F9FB]/80 via-transparent to-[#F8F9FB]/60 z-10 pointer-events-none" />
    </div>
  );
}
