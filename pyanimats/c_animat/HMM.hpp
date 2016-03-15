// HMM.h

#ifndef ANIMAT_HMM_H_
#define ANIMAT_HMM_H_

#include <vector>

#include "./rng.hpp"

using std::vector;

class HMM {
 public:
    HMM(vector<unsigned char> &genome, int start, const int numSensors,
            const int numHidden, const int numMotors,
            const bool deterministic);
    ~HMM();

    int mNumHidden;
    int mNumMotors;
    int mNumSensors;
    int mNumNodes;
    bool mDeterministic;

    vector< vector<unsigned char> > hmm;
    vector<unsigned int> sums;
    vector<unsigned char> ins, outs;
    unsigned char numInputs, numOutputs;

    void update(unsigned char *currentStates, unsigned char *nextStates);
};

#endif  // ANIMAT_HMM_H_