#!/bin/bash

curl --upload-file multi.json 'http://localhost:8215/?uri=http://example.com/graph/test&previous_version=0'

