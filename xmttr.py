###############################################################################
###############################################################################
#Copyright (c) 2020, citizenanalog
#See the file README.md for licensing information.
###############################################################################
###############################################################################

################################################################
#import modules
################################################################

from time import sleep,time
from datetime import datetime

from lndgrpc import LNDClient
from GUI import GUIThread as GUI

import helpers2,sys

#want to change some values for some objects in imported modules, so couldn't use "from" when importing specific objects.
#now, assign a shorter name to the specific objects of interest that will not be changed, but will be used frequently.

RoundAndPadToString=helpers2.RoundAndPadToString
TimeStampedPrint=helpers2.TimeStampedPrint


################################################################



################################################################
#define configuration related constants
################################################################

helpers2.PrintWarningMessages=True

LNDhost="127.0.0.1:10001"					#'alice' in simnet
LNDnetwork='testnet'						#'mainnet' or 'testnet'

CurrentRate=1							#sat/(FlowUnit)  // e.g. FlowUnit can be kg/min, lb/min, ect...
FlowUnitPerPayment=int(1000)					#set the mass flow unit/payment (1000 kg?)
RequiredPaymentAmount=int(FlowUnitPerPayment*CurrentRate)		#sat/payment 

################################################################


################################################################
#initialize variables
################################################################

OfferAccepted=False

TimeLastOfferSent=time()

FlowDelivered=0
FlowPaidFor=0

BigStatus='Insert Charge Cable Into Car'
SmallStatus='Waiting For Charge Cable To Be Inserted'

################################################################
#initialize the LND RPC
################################################################

lnd = LNDClient(LNDhost, network=LNDnetwork, admin=True)

################################################################

GUI.start()			#starts .run() (and maybe some other stuff?)

################################################################

try:

	while True:

		#pass values to the GUI
		GUI.Volts=Volts
		GUI.Amps=Amps
		GUI.BigStatus=BigStatus
		GUI.SmallStatus=SmallStatus
		GUI.FlowDelivered=FlowDelivered
		GUI.FlowPaidFor=FlowPaidFor
		GUI.CurrentRate=CurrentRate
		GUI.RequiredPaymentAmount=RequiredPaymentAmount
		GUI.FlowStartTime=FlowStartTime
		GUI.Proximity=Proximity
		GUI.MaxAmps=MaxAmps # not using this


		if GUI._stop_event.is_set():
			sys.exit()


		#not sure how to make ChargeNow perpetual, so just add an hour on every loop


		#print TheOutputVoltage

		if (TheOutputVoltage > ProximityVoltage-0.05) and (not Proximity):

			if (time()>ProximityLostTime+15):			#wait at least 15 seconds after the plug was removed to start looking for proximity again
				if ProximityCheckStartTime==-1:
					ProximityCheckStartTime=time()
					TimeStampedPrint("plug inserted")	#or was already inserted, but finished waiting 15 seconds
					BigStatus='Charge Cable Inserted'
					SmallStatus=''
				elif time()>ProximityCheckStartTime+3:		#proximity must be maintained for at least 3 seconds
					Proximity=True
					ReInsertedMessagePrinted=False
					ProximityCheckStartTime=-1

					LabJack.getFeedback(u3.BitStateWrite(4, RelayON))	# Set FIO4 to output ON
					TimeStampedPrint("relay energized")
					CurrentTime=time()
					InitialInvoice=True
					FlowDelivered=0
					FlowPaidFor=0


			elif not ReInsertedMessagePrinted:
				TimeStampedPrint("plug re-inserted in less than 15 seconds, waiting")
#need to add this waiting logic to the car unit as well, so that both wall and car unit are in sync and start measuring energy delivery at the same time.

				BigStatus='Waiting'
				SmallStatus=''

				ReInsertedMessagePrinted=True


			print(str(TheOutputVoltage))



		elif (TheOutputVoltage < ProximityVoltage-0.05*2) and (not Proximity) and (ProximityCheckStartTime!=-1 or ReInsertedMessagePrinted):
			ProximityLostTime=time()
			ReInsertedMessagePrinted=False
			ProximityCheckStartTime=-1
			TimeStampedPrint("plug was removed before the relay was energized")
			print(str(TheOutputVoltage))

			BigStatus='Charge Cable Removed'
			SmallStatus=''
			sleep(2)
			BigStatus='Insert Charge Cable Into Car'
			SmallStatus='Waiting For Charge Cable To Be Inserted'


		elif (TheOutputVoltage < ProximityVoltage-0.05*2) and (Proximity):
			Proximity=False
			ProximityLostTime=time()
			TimeStampedPrint("plug removed\n\n\n")
			print(str(TheOutputVoltage))

			BigStatus='Charge Cable Removed'
			SmallStatus=''
			sleep(2)
			BigStatus='Insert Charge Cable Into Car'
			SmallStatus='Waiting For Charge Cable To Be Inserted'

			#reset the values of current and voltage....actually, may not be needed here anymore ? need to remove and test.
			Volts	=	None
			Amps	=	None

			LabJack.getFeedback(u3.BitStateWrite(4, RelayOFF))	# Set FIO4 to output OFF



		Volts=WallUnit.voltsPhaseA
		Amps=WallUnit.reportedAmpsActual




		if Proximity:

			message = SWCAN.recv(timeout=.075)

			if PowerKilled:
				BigStatus='Stopped Charging'
				FlowStartTime=-1		#makes stop counting charge time even through there is still proximity

			else:

				if (Volts is not None) and (Amps is not None):		#should probably wait above when WallUnit object is created until these are available.
					PreviousTime=CurrentTime
					CurrentTime=time()
					deltaT=(CurrentTime-PreviousTime)/3600		#hours, small error on first loop when SWCANActive is initially True

					FlowDelivered+=deltaT*Volts*Amps		#W*hours // fix this with new units


				if OfferAccepted:

						if PendingInvoice:

							#check to see if the current invoice has been paid

							OutstandingInvoiceStatus=lnd.lookup_invoice(OutstandingInvoice.r_hash)
							if OutstandingInvoiceStatus.settled:
								FlowPaidFor+=OutstandingInvoiceStatus.value/(CurrentRate)		#W*hours
								PendingInvoice=False
								InitialInvoice=False							#reset every time just to make the logic simpler

								TimeStampedPrint('FlowUnitDelivered: '+RoundAndPadToString(FlowDelivered,1)+',   Volts: '+RoundAndPadToString(Volts,2)+',   Amps: '+RoundAndPadToString(Amps,2))
								TimeStampedPrint("payment received, time since last payment received="+str(time()-LastPaymentReceivedTime)+"s")

								LastPaymentReceivedTime=time()

								SmallStatus='Payment Received'


						#now that the pending invoices have been processed, see if it's time to send another invoice, or shutdown power if invoices haven't been paid in a timely manner.

						#time to send another invoice
						#adjust multiplier to decide when to send next invoice. can really send as early as possible because car just waits until it's really time to make a payment.
						#was 0.5, but higher is probably really better because don't know how long the lightning network payment routing is actually going to take.
						#send payment request after 10% has been delivered (90% ahead of time)
						#note, because below 1% error is allowed, this test may actually not have much meaning considering over the course of a charging cycle
						#the total error may be larger than an individual payment amount, so EnergyPaidFor-EnergyDelivered is likely less than 0 and therefor
						#a new invoice will just be sent right after the previous invoice was paid, rather than waiting.
						if ((FlowPaidFor-FlowDelivered)<RequiredPaymentAmount*0.90) and not PendingInvoice:
							RequiredPaymentAmount=FlowUnitPerPayment*CurrentRate				#sat

							OutstandingInvoice=lnd.add_invoice(RequiredPaymentAmount)

#need to do a try except here, because the buyer may not be listening properly
							SWCAN_ISOTP.send(OutstandingInvoice.payment_request.encode())			#send the new invoice using CAN ISOTP
							TimeStampedPrint("sent new invoice for "+str(RequiredPaymentAmount)+" satoshis")
							SmallStatus='Payment Requested'

							PendingInvoice=True

						elif PendingInvoice:									#waiting for payment
							#TimeStampedPrint("waiting for payment, and limit not yet reached")
							pass

						else:
							#TimeStampedPrint("waiting to send next invoice")
							pass



				else:
					#try to negotiate the offer
					if (message is not None) and (message.arbitration_id == 1999 and message.data[0]==1):		#don't really need to convert to int since hex works fine for a 0 vs 1
						#buyer accepted the rate
						OfferAccepted=True
						TimeStampedPrint("buyer accepted rate")

						FlowStartTime=datetime.now()

						BigStatus='Charging'
						SmallStatus='Sale Terms Accepted'

						FirstRequiredPaymentAmount=1*RequiredPaymentAmount				#sat, adjust multiplier if desire the first payment to be higher than regular payments.

						OutstandingInvoice=lnd.add_invoice(FirstRequiredPaymentAmount)
						SWCAN_ISOTP.send(OutstandingInvoice.payment_request.encode())
						TimeStampedPrint("sent first invoice for "+str(FirstRequiredPaymentAmount)+" satoshis")

						LastPaymentReceivedTime=time()			#fudged since no payment actually received yet, but want to still time since invoice sent, and need variable to be initialized.

						PendingInvoice=True

					elif (message is not None) and (message.arbitration_id == 1999 and message.data[0]==0):
						OfferAccepted=False
						TimeStampedPrint("buyer rejected rate")
						#SmallStatus='Sale Terms Rejected'

					elif (TimeLastOfferSent+1)<time():			#only send once per second and give the outer loop a chance to process all incoming messages, otherwise will send multiple offers in between the tesla messages and the car module messages.
						#provide the offer

#need to do a try except here, because the buyer may not be listening properly
						SWCAN.send(Message(arbitration_id=1998,data=int(FlowUnitPerPayment).to_bytes(4, byteorder='little')+int(RequiredPaymentAmount).to_bytes(4, byteorder='little'),is_extended_id=False))
						TimeLastOfferSent=time()
						TimeStampedPrint("provided an offer of "+RoundAndPadToString(FlowUnitPerPayment,1)+" W*hour for a payment of "+str(RequiredPaymentAmount)+" satoshis ["+RoundAndPadToString(CurrentRate,1)+" satoshis/(W*hour)]")
						SmallStatus='Provided An Offer'
						#SmallStatus='Sale Terms Offered To Vehicle'



				if (
						#buyer must pay ahead 20% for all payments but the first payment (must pay after 80% has been delivered).
						#also allow 1% error due to measurement error as well as transmission losses between the car and the wall unit.
						#this error basically needs to be taken into consideration when setting the sale rate.
						(((FlowPaidFor-FlowDelivered*0.99)<FlowUnitPerPayment*0.20)	and not	InitialInvoice)

							or

						#buyer can go into debt 30% before the first payment, also allowing for 1% error as above, although that may be really needed for the first payment.
						(((FlowPaidFor-FlowDelivered*0.99)<-FlowUnitPerPayment*0.30)	and	InitialInvoice)
					):

					TimeStampedPrint("buyer never paid, need to kill power")
					PowerKilled=True
					TWCManager.master.sendStopCommand()					#need to refine this statement if have multiple wall units.
					SmallStatus='Vehicle Did Not Make Payment'





		else:
			OfferAccepted=False
			PowerKilled=False

			sleep(.075*3)		#make this longer than the receive timeouts so that the buffers always get empty, otherwise there will be a reaction delay because the receiver is still processing old messages????



except (KeyboardInterrupt, SystemExit):

	TWCManager.MainThread.stop()
	TWCManager.MainThread.join()
	GUI.stop()
	GUI.join()	#for some reason if this is not used, python tries too quit before the stop command is received by the thread and it gracefully shutdown and then it takes longer for tk to timeout and close the interpreter?

	TimeStampedPrint("quitting")

except:
	raise

finally:

	TimeStampedPrint("SystemExit\n\n\n")




