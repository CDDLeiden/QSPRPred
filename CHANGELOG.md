# Change Log
From v1.2.0 to v1.3.0

## Fixes

- problems with PaDEL descriptors and fingerprints on Linux were fixed

## Changes

- `QSPRModel` metadata now contains two extra entries:
  1. `model_class` - the fully qualified class name of the model
  2. `version` - the version of QSPRPred used to save the model
  - this change is not compatible with older files, but you can manually add these two entries and it should work fine in the newer version

## New Features

- The `QSPRModel.fromFile()` method can now instantiate a model from a file directly without knowing the underlying model type. It simply uses the class path stored in the model metadata file now.
