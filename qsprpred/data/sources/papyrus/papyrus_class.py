"""
papyrus_class

Created by: Martin Sicho
On: 06.10.22, 14:28
"""
import os
from pathlib import Path
from typing import List

from papyrus_scripts.download import download_papyrus

from qsprpred.data.data import MoleculeTable
from qsprpred.data.sources.papyrus.papyrus_filter import papyrus_filter

class Papyrus:
    DEFAULT_DIR = os.path.join(Path.home(), '.Papyrus')
    os.makedirs(DEFAULT_DIR, exist_ok=True)

    def __init__(
            self,
            data_dir : str = DEFAULT_DIR,
            version : str = 'latest',
            descriptors : list = tuple(),
            stereo : bool = False,
            disk_margin : float = 0.01
    ):
        """
        Create new instance of Papyrus dataset. See `papyrus_filter` and `Papyrus.download` and `Papyrus.getData` for more details.

        Args:
            data_dir: storage directory for Papyrus database and the extracted data files
            version: Papyrus database version
            descriptors: descriptors to download if not already present
            stereo: include stereochemistry in the database
            disk_margin: the disk space margin to leave free
        """
        self.data_dir = data_dir
        self.version = version
        self.descriptors = descriptors
        self.stereo = stereo
        self.nostereo = not self.stereo
        self.plusplus = not self.stereo
        self.disk_margin = disk_margin

    def download(self):
        """
        Download Papyrus database with the required information. Only newly requested data is downloaded.

        Returns:
            `None`
        """

        download_papyrus(
            outdir=self.data_dir,
            version=self.version,
            descriptors=self.descriptors,
            stereo=self.stereo,
            nostereo=self.nostereo,
            disk_margin=self.disk_margin,
        )

    def getData(
            self,
            acc_keys: List[str],
            quality: str,
            name : str = None,
            drop_duplicates: bool = False,
            chunk_size : int = 1e5,
            use_existing : bool = True
    ):
        """
        Get the data from the Papyrus database as a `DataSetTSV` instance.

        Args:
            acc_keys: protein accession keys
            quality: desired minimum quality of the dataset
            name: name of the dataset (this is the prefix of the generated .tsv file)
            drop_duplicates: remove duplicates after filtering
            chunk_size: data is read in chunks of this size (see `papyrus_filter`)
            use_existing: if the data is already present, use it instead of extracting it again

        Returns:

        """

        self.download()
        data, path =  papyrus_filter(
            acc_key=acc_keys,
            quality=quality,
            outdir=self.data_dir,
            prefix=name,
            drop_duplicates=drop_duplicates,
            chunk_size=chunk_size,
            use_existing=use_existing,
            stereo=self.stereo,
            plusplus=self.plusplus,
        )
        return MoleculeTable.fromFile(path, df=data)