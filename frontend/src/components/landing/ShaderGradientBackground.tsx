'use client';
import { ShaderGradientCanvas, ShaderGradient } from 'shadergradient';

const ShaderGradientComponent = ShaderGradient as any;

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
        <ShaderGradientComponent
          control="props"
          animate="on"
          type="waterPlane"
          color1="#bac0be"
          color2="#beb6be"
          color3="#635f61"
          brightness={1.1}
          cAzimuthAngle={180}
          cDistance={3.9}
          cPolarAngle={115}
          cameraZoom={1}
          envPreset="city"
          grain="off"
          lightType="3d"
          positionX={-0.5}
          positionY={0.1}
          positionZ={0}
          reflection={0.1}
          rotationX={0}
          rotationY={0}
          rotationZ={235}
          shader="defaults"
          uAmplitude={0}
          uDensity={1.1}
          uFrequency={5.5}
          uSpeed={0.1}
          uStrength={2.4}
          uTime={0.2}
          wireframe={false}
        />
      </ShaderGradientCanvas>
      {/* Soft gradient fade into page content */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/20 via-transparent to-[#F8F9FB] z-10 pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#F8F9FB]/80 via-transparent to-[#F8F9FB]/60 z-10 pointer-events-none" />
    </div>
  );
}
