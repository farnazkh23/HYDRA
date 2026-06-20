import logoHydra from "../assets/Logo-HYDRA.png";

export function HydraLogo() {
  return (
    <div className="flex items-center gap-3">
      <img
        src={logoHydra}
        alt="HYDRA"
        className="h-14 w-auto object-contain drop-shadow-[0_0_18px_rgba(163,255,65,0.65)]"
      />
    </div>
  );
}

export default HydraLogo;
