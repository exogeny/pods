import os
import uuid
import collections

import tensorflow as tf
import tensorflow_datasets as tfds
from tensorflow_datasets.core import dataset_collection_builder
from tensorflow_datasets.core import naming

from proteomics_datasets import utils


Split = collections.namedtuple(
    'Split', ['name', 'cell_line']
)


class HumanProteinAtlasCollection(dataset_collection_builder.DatasetCollection):

  @property
  def info(self):
    return dataset_collection_builder.DatasetCollectionInfo.from_cls(
      dataset_collection_class=self.__class__,
      description='Human Protein Atlas subcellular datasets',
      release_notes={
        '1.0.0': 'Initial release.',
      },
    )

  @property
  def datasets(self):
    current_folder = os.path.dirname(os.path.abspath(__file__))
    cell_lines = os.listdir(os.path.join(current_folder, 'cell_lines'))
    cell_lines = [c for c in cell_lines if 'images.csv' in c]
    cell_lines = [c.replace('_images.csv', '') for c in cell_lines]

    return collections.OrderedDict({
      "1.0.0": naming.references_for(
        {
          cell_line: f'Cell line {cell_line}'
          for cell_line in cell_lines
        }
      )
    })


class HumanProteinAtlasConfig(tfds.core.BuilderConfig):

  def __init__(self, splits=None, **kwargs):
    super(HumanProteinAtlasConfig, self).__init__(
        version=tfds.core.Version('1.1.0'), **kwargs)
    self.splits = splits


class HumanProteinAtlas(tfds.core.GeneratorBasedBuilder):

  VERSION = tfds.core.Version('1.0.0')
  RELEASE_NOTES = {
    '1.0.0': 'Initial release.',
  }
  BUILDER_CONFIGS = [
    HumanProteinAtlasConfig(
      name='U2OS',
      splits=[
        Split(name=tfds.Split.TRAIN, cell_line='U2OS'),
        Split(name=tfds.Split.TEST, cell_line='U2OS'),
      ]),
    HumanProteinAtlasConfig(
      name='A-431',
      splits=[
        Split(name=tfds.Split.TRAIN, cell_line='A-431'),
        Split(name=tfds.Split.TEST, cell_line='A-431'),
      ]),
    HumanProteinAtlasConfig(
      name='HEK293',
      splits=[
        Split(name=tfds.Split.TRAIN, cell_line='HEK293'),
        Split(name=tfds.Split.TEST, cell_line='HEK293'),
      ]),
    HumanProteinAtlasConfig(
      name='U-251MG',
      splits=[
        Split(name=tfds.Split.TRAIN, cell_line='U-251MG'),
        Split(name=tfds.Split.TEST, cell_line='U-251MG'),
      ]),
  ]

  def _info(self):
    return self.dataset_info_from_configs(
      features=tfds.features.FeaturesDict({
        'ensg/id': tfds.features.Text(),
        'ensg/name': tfds.features.Text(),

        'image': tfds.features.Image(encoding_format='png'),
        'image/mask': tfds.features.Image(encoding_format='png'),

        'location/main/level1': tfds.features.Tensor(shape=(3,), dtype=tf.int64),
        'location/main/level2': tfds.features.Tensor(shape=(13,), dtype=tf.int64),
        'location/main/level3': tfds.features.Tensor(shape=(34,), dtype=tf.int64),
        'location/additional/level1':tfds.features.Tensor(shape=(3,), dtype=tf.int64),
        'location/additional/level2': tfds.features.Tensor(shape=(13,), dtype=tf.int64),
        'location/additional/level3': tfds.features.Tensor(shape=(34,), dtype=tf.int64),
        'location/extracellular/level1': tfds.features.Tensor(shape=(3,), dtype=tf.int64),
        'location/extracellular/level2': tfds.features.Tensor(shape=(13,), dtype=tf.int64),
        'location/extracellular/level3': tfds.features.Tensor(shape=(34,), dtype=tf.int64),
        'location/reliability': tfds.features.Text(),
      }),
    )

  def _split_generators(self, dl_manager):
    _internal_dl_manager = tfds.download.DownloadManager(
        download_dir=os.path.join(dl_manager.download_dir, 'protein_atlas'))
    cell_lines = set([split.cell_line for split in self.builder_config.splits])
    
    # prepare download url
    image_infos = {}
    download_urls = {}

    current_folder = os.path.dirname(os.path.abspath(__file__))
    for cell_line in cell_lines:
      url_path = os.path.join(current_folder, 'cell_lines', f'{cell_line}_images.csv')
      with tf.io.gfile.GFile(url_path, 'r') as f:
        url_lines = f.readlines()[1:]
        url_lines = [tuple(l.strip().split(',')) for l in url_lines]

        image_infos[cell_line] = []
        download_urls[cell_line] = {}
        for assay_id, image_id, gene_id, _ in url_lines:
          key = f'{assay_id}-{image_id}'
          image_infos[cell_line].append((assay_id, image_id, gene_id, gene_id))
          download_urls[cell_line][f'{key}-s'] = f'https://www.proteinatlas.org/images_cell_segmentation/{assay_id}/{image_id}_segmentation.png'
          download_urls[cell_line][f'{key}-c'] = f'https://images.proteinatlas.org/{assay_id}/{image_id}_blue_red_green.jpg'
          download_urls[cell_line][f'{key}-y'] = f'https://images.proteinatlas.org/{assay_id}/{image_id}_yellow.jpg'

    # download images
    download_urls['location_file'] = 'https://v23.proteinatlas.org/download/subcellular_location.tsv.zip'
    downloaded_paths = _internal_dl_manager.download(download_urls)
    extracted_location_folder = _internal_dl_manager.extract(downloaded_paths['location_file'])
    extracted_location_file = os.path.join(str(extracted_location_folder), 'subcellular_location.tsv')

    # read the subcellular location file
    subcellular_locations = utils.get_subcellular_locations(extracted_location_file)

    splits = []
    for split in self.builder_config.splits:
      splits.append(tfds.core.SplitGenerator(
        name=split.name,
        gen_kwargs=dict(
          split_name=split.name,
          image_infos=image_infos[split.cell_line],
          image_paths=downloaded_paths[split.cell_line],
          subcellular_locations=subcellular_locations,
        )
      ))
    return splits


  def _generate_examples(self, split_name, image_infos, image_paths, subcellular_locations):
    for assay_id, image_id, gene_id, gene_name in image_infos:
      key = f'{assay_id}-{image_id}'
      image = utils.read_hpa_image(image_paths[f'{key}-c'], image_paths[f'{key}-y'])
      location = subcellular_locations.get(gene_id, None)
      location_ids = utils.get_location_ids(location)

      for example in utils.generate_examples_from_image(image,
                                                        image_paths[f'{key}-s'],
                                                        split_name):
        example.update({
          'ensg/id': gene_id,
          'ensg/name': gene_name,
        })

        index = str(uuid.uuid4())
        example.update(location_ids)
        yield f'{key}-{index}', example
