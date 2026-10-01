// Review override only; source GLB materials and embedded textures stay intact.
export function useGreyMaterials(loader,THREE){
 loader.register(()=>({name:'STREP_grey_review',loadMaterial:()=>Promise.resolve(new THREE.MeshStandardMaterial({color:0x9b9fa5,roughness:.8}))}));
}
