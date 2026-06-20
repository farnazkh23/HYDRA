import logoAsset from "@/assets/hydra-final-logo.png.asset.json";

export function HydraLogo({ size = 36 }: { size?: number }) {
  return (
    <span
      className="inline-block shrink-0 dark:[filter:drop-shadow(0_0_6px_oklch(0.92_0.22_128/0.45))]"
      style={{ width: size, height: size }}
      aria-label="HYDRA logo"
    >
      <img
        src={logoAsset.url}
        alt="HYDRA"
        width={size}
        height={size}
        className="block h-full w-full object-contain"
        draggable={false}
      />
    </span>
  );
}
