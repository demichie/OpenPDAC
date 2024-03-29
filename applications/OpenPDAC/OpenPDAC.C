/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     | Website:  https://openfoam.org
    \\  /    A nd           | Copyright (C) 2011-2021 OpenFOAM Foundation
     \\/     M anipulation  |
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

Application
    OpenPDAC

Description
    Solver for a system of any number of compressible fluid phases with a
    common pressure, but otherwise separate properties. The type of phase model
    is run time selectable and can optionally represent multiple species and
    in-phase reactions. The phase system is also run time selectable and can
    optionally represent different types of momentum, heat and mass transfer.

\*---------------------------------------------------------------------------*/

#include "fvCFD.H"
#include "dynamicFvMesh.H"
#include "phaseSystem.H"
//#include "phaseCompressibleMomentumTransportModel.H"
#include "phaseDynamicMomentumTransportModel.H"
#include "pimpleControl.H"
#include "pressureReference.H"
#include "localEulerDdtScheme.H"
#include "fvcSmooth.H"

#include "parcelCloudList.H"
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

int main(int argc, char *argv[])
{
    #include "postProcess.H"

    #include "setRootCaseLists.H"
    #include "createTime.H"
    #include "createDynamicFvMesh.H"
    #include "createDyMControls.H"
    #include "createFields.H"
    #include "createFieldRefs.H"

    if (!LTS)
    {
        #include "CourantNo.H"
        #include "setInitialDeltaT.H"
    }

    Switch faceMomentum
    (
        pimple.dict().lookupOrDefault<Switch>("faceMomentum", false)
    );
    Switch partialElimination
    (
        pimple.dict().lookupOrDefault<Switch>("partialElimination", false)
    );

    #include "createRDeltaTf.H"

    // * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

    Info<< "\nStarting time loop\n" << endl;
    
    if (pimple.dict().lookupOrDefault<bool>("hydrostaticInitialisation", false))
    {
        scalar startTime_ = runTime.startTime().value();
        scalar deltaT = runTime.deltaT().value();

        // set small value for deltaT to evolve particles    
        runTime.setDeltaT(1.e-5*deltaT);

        // increase time iterator            
        runTime++;
    
        // evolve particle cloud
        clouds.evolve();

        // restore startTime
        runTime.setTime(startTime_,startTime_);
                
        // restore deltaT            
        runTime.setDeltaT(deltaT);

        // write everything (including lagrangian)
        runTime.writeNow();
    }    

    while (pimple.run(runTime))
    
    {
        #include "readDyMControls.H"

        int nEnergyCorrectors
        (
            pimple.dict().lookupOrDefault<int>("nEnergyCorrectors", 1)
        );

        if (LTS)
        {
            #include "setRDeltaT.H"
            if (faceMomentum)
            {
                #include "setRDeltaTf.H"
            }
        }
        else
        {
            #include "CourantNo.H"
            #include "setDeltaT.H"
        }
        
        runTime++;
        Info<< "Time = " << runTime.timeName() << nl << endl;

		//clouds.storeGlobalPositions();

        // --- Pressure-velocity PIMPLE corrector loop
        while (pimple.loop())
        {
            if (!pimple.flow())
            {
                if (pimple.models())
                {
                    fvModels.correct();
                }

                if (pimple.thermophysics())
                {
                    fluid.solve(rAUs, rAUfs);
                    fluid.correct();
                    fluid.correctContinuityError();

                    #include "YEqns.H"
                    #include "EEqns.H"
                    #include "pEqnComps.H"

                    forAll(phases, phasei)
                    {
                        phases[phasei].divU(-pEqnComps[phasei] & p_rgh);
                    }
                }
            }
            else
            {
                if (pimple.firstPimpleIter() || moveMeshOuterCorrectors)
                {
                    // Store divU from the previous mesh so that it can be
                    // mapped and used in correctPhi to ensure the corrected phi
                    // has the same divergence
                    tmp<volScalarField> divU;

                    if
                    (
                        correctPhi
                    )
                    {
                        // Construct and register divU for mapping
                        divU = new volScalarField
                        (
                            "divU0",
                            fvc::div
                            (
                                fvc::absolute(phi, fluid.movingPhases()[0].U())
                            )
                        );
                    }

                    fvModels.preUpdateMesh();

                    mesh.update();

                    if (mesh.changing())
                    {
                        gh = (g & mesh.C()) - ghRef;
                        ghf = (g & mesh.Cf()) - ghRef;

                        fluid.meshUpdate();

                        if (correctPhi)
                        {
                            fluid.correctPhi
                            (
                                p_rgh,
                                divU,
                                pressureReference,
                                pimple
                            );
                        }

                        if (checkMeshCourantNo)
                        {
                            #include "meshCourantNo.H"
                        }
                    }
                }

                if (pimple.models())
                {
                    fvModels.correct();
                }

                fluid.solve(rAUs, rAUfs);
                fluid.correct();
                fluid.correctContinuityError();

                if (pimple.thermophysics())
                {
                    #include "YEqns.H"
                }

                if (faceMomentum)
                {
                    #include "pUf/UEqns.H"

                    if (pimple.thermophysics())
                    {
                        #include "EEqns.H"
                    }

                    #include "pUf/pEqn.H"
                }
                else
                {
                    #include "pU/UEqns.H"

                    if (pimple.thermophysics())
                    {
                        #include "EEqns.H"
                    }

                    #include "pU/pEqn.H"
                }

                fluid.correctKinematics();

                if (pimple.turbCorr())
                {
                    fluid.correctTurbulence();
                }
            }
        }

		mu = muC * pow( 1.0 - ( 1.0 - phases[carrierIdx] ) / 0.62 , -1.55);
		U = fluid.U();
		rho = fluid.rho();
		
		Info<< "min mu " << min(mu).value() << " max mu " << max(mu).value() << endl;

        clouds.evolve();

        runTime.write();

        Info<< "ExecutionTime = "
            << runTime.elapsedCpuTime()
            << " s\n\n" << endl;
    }

    Info<< "End\n" << endl;

    return 0;
}


// ************************************************************************* //
