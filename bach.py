from inspect import isclass
from operator import mod
from statistics import mode
import music21
import pickle
import sys
import os
from tqdm import tqdm
import uuid

from bach_utils import *


def main():
    should_generate_indices = False
    should_generate_datasets = False
    should_generate_batch = False
    is_mxl = False
    is_comp = False
    filename = ''
    sequence_str = ''
    batch_path = ''

    if len(sys.argv) == 1:
        print("Usage: bach.py [--generate_indices, --generate_datasets, --mxl, --comp, --generate_batch] filename [sequence_str, batch_path]")
        exit(1)

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == '--generate_indices':
            should_generate_indices = True
        elif sys.argv[i] == '--generate_datasets':
            should_generate_datasets = True
        elif sys.argv[i] == '--generate_batch':
            should_generate_batch = True
        elif sys.argv[i] == '--mxl':
            is_mxl = True
        elif sys.argv[i] == '--comp':
            is_comp = True
        elif filename == '':
            filename = sys.argv[i]
        elif (should_generate_batch or is_mxl) and batch_path == '':
            batch_path = sys.argv[i]
        else:
            sequence_str = sys.argv[i]

    if should_generate_indices:
        note_indices, indices_note, _, _  = generate_database()
        write_note_indices_to_file(note_indices, indices_note)
    else:
        note_indices, indices_note = read_note_indices_from_file()

    if should_generate_datasets:
      print('Generating major/minor datasets')
      note_indices, indices_note, major_dataset, minor_dataset = generate_database()
      print(f'Writing datasets to {filename}_major.txt and {filename}_minor.txt')
      write_dataset_to_file(major_dataset, indices_note, f'{filename}_major.txt')
      write_dataset_to_file(minor_dataset, indices_note, f'{filename}_minor.txt')

    elif is_mxl:
        chorale = music21.converter.parse(filename)
        # save(chorale, f'{filename.split(".mxl")[0]}-gen')
        chorale.metadata.title = ''
        path = batch_path + str(uuid.uuid4().hex)
        print(f'filename: {path}')
        save(chorale, path)
        exit(0)

    elif should_generate_batch:
      generate_batch(filename, batch_path, is_comp, note_indices, indices_note)
      exit(0)

    elif sequence_str != '':
      # Convert sequence string to music21 score
      if not is_comp:
        chorale_seq = pitch_with_harmony_sequence(sequence_str, note_indices)
      else:
        chorale_seq = pitch_with_harmony_sequence_non_hidden(sequence_str, note_indices)
      chorale = harmony_sequence_to_chorale(chorale_seq, note_indices, indices_note)


      # Transpose key to G harmonic minor
      interval = music21.interval.Interval(music21.pitch.Pitch('C'), music21.pitch.Pitch('G'))
      chorale_transposed = chorale.transpose(interval)
      print(f'filename: {filename}')
      print(f'chorale: {chorale_transposed}')
      save(chorale_transposed, filename)

      # print(f'note indices len: {len(note_indices)}')
      # print(f'indices note len: {len(indices_note)}')
      # print(f'sequence_str: {sequence_str}')
      # print(f'filename: {filename}')
      # print(f'chorale: {chorale}')

      # save(chorale, filename)

def generate_batch(filename, batch_path, is_comp, note_indices, indices_note):
  # print(f'{filename}, {batch_path}, {is_comp}, {note_indices}, {indices_note}')
  with open(filename, 'r') as batch_file:
    for i, sequence_str in enumerate(batch_file.readlines()):
      # Convert sequence string to music21 score
      if not is_comp:
        chorale_seq = pitch_with_harmony_sequence(sequence_str, note_indices)
      else:
        chorale_seq = pitch_with_harmony_sequence_non_hidden(sequence_str, note_indices)
      chorale = harmony_sequence_to_chorale(chorale_seq, note_indices, indices_note)

      # Transpose key to G harmonic minor
      interval = music21.interval.Interval(music21.pitch.Pitch('C'), music21.pitch.Pitch('G'))
      chorale_transposed = chorale.transpose(interval)

      path = batch_path + str(uuid.uuid4().hex)
      print(f'=============  {i+1}  =============')
      print(f'filename: {path}')
      save(chorale_transposed, path)

    
def generate_database():
    note_set = set()
    note_set.add(START)
    note_set.add(END)
    note_set.add(HOLD)
    note_set.add(NC)
    note_set.add(REST)

    for chorale in music21.corpus.chorales.Iterator():
        for note in chorale.parts[0].flat.notesAndRests: # only extracting from first part (soprano)
            # print(note)
            note_set.add(note_to_str(note))
    note_indices = dict((c, i) for i, c in enumerate(note_set))
    indices_note = dict((i, c) for i, c in enumerate(note_set))

    parts_count = 4
    tick = 1 / SUBDIVISION  # each beat is subdivided by 4 (so 1 tick is a sixteenth note)
    sequence_beats = 20  # 20 beats per training sequence
    sequence_length = sequence_beats * SUBDIVISION

    # Get note sequences from each chorale transposed to a common key
    chorale_dataset_major = []
    chorale_dataset_minor = []

    # Iterate through chorales to get notes at each timestep
    for chorale_id, chorale in tqdm(enumerate(music21.corpus.chorales.Iterator())):
        key = chorale.analyze('key')
        interval = music21.interval.Interval(key.tonic, music21.pitch.Pitch('C'))
        chorale_transposed = chorale.transpose(interval)

        if len(chorale.parts) == parts_count:
            chorale_transposed_sequence = []
            for i in range(parts_count):
                chorale_transposed_sequence.append(chorale_to_sequence(chorale_transposed.parts[i], 0.0,
                                                                chorale_transposed.parts[i].flat.highestTime,
                                                                note_indices, indices_note))
            if key.name[-5:] == 'major':
                chorale_dataset_major.append(chorale_transposed_sequence)
            elif key.name[-5:] == 'minor':
                chorale_dataset_minor.append(chorale_transposed_sequence)
            # print(f'{key} -> {chorale_transposed.analyze("key")}  {interval} *{key.name[-5:]}*')

    print(f'note_indices length: {len(note_indices)}')
    return (note_indices, indices_note, chorale_dataset_major, chorale_dataset_minor)


def read_note_indices_from_file():
    with open(NOTE_INDICES_CACHE_FILE, 'rb') as file:
        note_indices, indices_note = pickle.load(file)
    return (note_indices, indices_note)
    

def write_note_indices_to_file(note_indices, indices_note):
    with open(NOTE_INDICES_CACHE_FILE, 'ab') as file:
        pickle.dump((note_indices, indices_note), file)


# Print chorale sequence dataset for Markov model
def write_dataset_to_file(dataset, indices_note, filename):
  with open(filename, 'w') as data_file:
    for chorale_seq in dataset:
      beat_metadata = get_beat_metadata(chorale_seq[0])
      chorale_string = ''
      for i, note_index in enumerate(chorale_seq[0]):
        note = indices_note[note_index]
        harmony_note_1 = indices_note[chorale_seq[1][i]]
        harmony_note_2 = indices_note[chorale_seq[2][i]]
        harmony_note_3 = indices_note[chorale_seq[3][i]]
        # chorale_string += f'{note},{beat_metadata[i]}:{harmony_note} '
        # Hidden Markov (CHiMP) with 4 voices
        chorale_string += f'{harmony_note_1},{harmony_note_2},{harmony_note_3}:{note},{beat_metadata[i]} '
        # Non-Hidden Markov (CoMP) with 4 voices
        # chorale_string += f'{note},{harmony_note_1},{harmony_note_2},{harmony_note_3},{beat_metadata[i]}:{note},{harmony_note_1},{harmony_note_2},{harmony_note_3},{beat_metadata[i]} '
      chorale_string += '\n'
      # print(chorale_string)
      data_file.write(chorale_string)


# Print chorale sequence dataset for Markov model
# Formatted as raw sequences:
# C4:C4 __:__ __:__ __:__ C4:C4 __:__ __:__ __:__ __:__ __:__ __:__ __:__
def write_raw_dataset_to_file(dataset, indices_note, filename):
  with open(filename, 'w') as data_file:
    for chorale_seq in dataset:
      chorale_string = ''
      for note_index in chorale_seq:
        note = indices_note[note_index]
        chorale_string += f'{note}:{note} '
      chorale_string += '\n'
      # print(chorale_string)
      data_file.write(chorale_string)


# Print chorale sequence dataset for Markov model
# Formatted as duration sequences:
# C4-4:C4-4 C4-8:C4-8 G4-4:G4-4
def write_rhythm_dataset_to_file(dataset, note_indices, indices_note, filename):
  with open(filename, 'w') as data_file:
    for chorale_seq in dataset:
      duration = 0
      note = START
      chorale_string = ''
      for note_index in chorale_seq:
        if note_index == note_indices[HOLD]:
          duration += 1
        else:
          if note != START:
            chorale_string += f'{note}-{duration}:{note}-{duration} '
          note = indices_note[note_index]
          duration = 1
      chorale_string += '\n'
      data_file.write(chorale_string)


if __name__ == '__main__':
    main()
