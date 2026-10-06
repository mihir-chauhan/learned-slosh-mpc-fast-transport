Config files for our method. One file per (experiment group, variant). Name them
`<group>__<variant>.yaml`, e.g. `main__ours.yaml`, `abl_components__no_gate.yaml`.
Runs reference the config with `rh run --config <path>` so the registry keeps the exact settings.
