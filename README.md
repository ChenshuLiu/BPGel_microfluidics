# BPGel_microfluidics
## Description
This repository contains the microfluidic tracking and analysis pipeline used to quantify hydrogel(BPGel)-actuated fluid transport in a wearable microfluidic–electrochemical biosensing system. The project supports the manuscript \textit{"Hydrogel-actuated microfluidic wearable system for in situ detection of solid-state epidermal macromolecules"}. The tracking framework enables time-resolved visualization and quantification of buffer propagation, transported volume, and flow rate within a skin-conformal microfluidic channel driven by a temperature-responsive hydrogel pump.

![abstract](graphical_abstract.png)
Upon being placed on the surface of the skin, the change in temperature drive conformational change in the BPGel that prompt buffer releasing (\textbf{Figure a}). The released buffer progress through a curved microchannel in the microfluidic chamber (\textbf{Figure b}). Using the code provided in this repository, the cumulative change in volume and buffer flow rate can be tracked (\textbf{Figure c}).

## Deployment
Change to directory of your project. Create virtual environment and load the dependencies according to `requirements.txt`.
```
python -m venv [name of virtual environment]
source [name of virtual environment]/bin/activate
pip install -r ./requirements.txt
```
