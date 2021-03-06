import random
import numpy as np

# lsgai

## TODO missing values?? (genotypes of NN)

### Globals ###
GENO_LEN = 10 	# num SNPs in geno # may not know ahead of time bc filter sites
NOT_REP = 9    	# '-' in orig hapmap data
MISSING = -9  	# 'N'in orig hapmap data

# population codes (strings for now, could be ints)
ASW = 'ASW' # african americans in SW usa
CEU = 'CEU' # northern european-amer in utah
CHB = 'CHB' # han chinese in beijing
CHD = 'CHD' # chinese in denver, colorado
GIH = 'GIH' # gujarati in houston, texas
JPT = 'JPT' # jp in tokyo
LWK = 'LWK' # luhya in webuye, kenya
MEX = 'MEX' # mexican-amer in LA
MKK = 'MKK' # maasai in kinyawa, kenya
TSI = 'TSI' # toscan in italy
YRI = 'YRI' # yoruba in italy

#truePopsL = [ASW, CEU, CHB, CHD, GIH, JPT, LWK, MEX, MKK, TSI, YRI]

### Classes ###
class FullGenotype:
	'''reference and alternate allele(s)'''

	def __init__(self):
		# ref allele (a where aa = 0) and alt allele (A where AA = 2)
		# for this chr, sites with more than two variants are filtered out
		refAlleles = []
		altAlleles = []

		# list allowing multiple alt alleles (i.e. 1 to 3 alt alleles)
		# measure how many sites actually have multiple alts 
		# (see if i'm losing sig amount of info)
		variantCounts = []
		allelesMulti = [] # tuples of (ref, alt1, <alt2>, <alt3>)
		# TODO will probably discard sites with multiple variants 
		# (assuming very few such sites and lots of two-variant sites left to use), 
		#	unless can think of a way to calculate the likelihood 
		# 	p^g + (1-p)^(2-g) won't cut it
		# TODO undecided on sites where no variation in the populations used

class Individual:
	'''Genotype 0/1/2 for each site (with special values) and label'''
	# shared variables here: (not sure if I need any)

	# initiator
	def __init__(self, 
				pop, 
				indivID):
		self.truePop = pop 	# keep track of pop for later graph coloring/labeling
		self.indivID = indivID

		self.j = None 		# their index in indivs list and corresponding geno matrix
		self.assignedPop = None
		#self.assignedPop2 = None # TODO if i want to compare how same indiv is clustered under two schemes?
		self.geno = [] 		# will be converted to np array once all snps read in
		self.famID = None 	# mom, dad, child all have same famID
		self.momID = None
		self.dadID = None
		self.sex = None		# 0 = unknown, 1 or 2 otherwise

	def prettyprint(self, verbose = False, printGeno = False):
		'''print fields of an individual. not that pretty but ok'''
		print("indivID:\t%s" % self.indivID)
		print("truePop:\t%s" % self.truePop)
		print("assignedPop:\t%s" % self.assignedPop)

		if verbose:
			print("famID:\t\t%s" % self.famID)
			print("momID:\t\t%s" % self.momID)
			print("dadID:\t\t%s" % self.dadID)
			print("sex:\t\t%s" % self.sex)

		if printGeno:
			print("geno:\n")
			print(list[self.geno])



def parseFile(fileName, pop):
	'''given hapmap formatted data, get 0/1/2 genotypes for individuals.
	return list of Individuals '''

	# 0		1		2	3	4		5		6		7			8		9		  10	11
	#rs# alleles chrom pos strand assembly# center protLSID assayLSID panelLSID QCcode NA21741 NA21740
	
	variantCounts = []
	allelesMulti = [] # tuples of (ref, <alt1>, <alt2>, <alt3>) (alts are optional)

	with open(fileName, 'r') as inf:

		# read header
		indivIDs = inf.readline().rstrip().split()[11:]
		indivs = [] # list of Individuals

		for indivID in indivIDs:
			indivs.append(Individual(pop, indivID))

		numIndiv = len(indivs) # number of indivs in file (subsample)
		
		# read info for each snp
		# NOTE: snps must be in same order in all files, same number of snps
		#		i.e. the ith snp in file has to be same site as in another file
		for line in inf:
			lineL = line.strip().split()
			ref, alt = lineL[1].split("/") # e.g. A/C
			allelesMulti.append((ref,alt))

			# update each individual's genotype with current snp
			for j in range(numIndiv):
				geno = lineL[11 + j] # e.g. AG
				# NN indicates missing values. arbitrarily handle NN by making it het
				# not the most statistically robust way, but NN rare and it's easy
				if geno == "NN":
					indivs[j].geno.append(1)
					continue

				g = (geno[0] == alt) + (geno[1] == alt) # e.g. 0/1/2, 0 for ref
				indivs[j].geno.append(g)

		# after all snps are appended, convert to arrays
		for indiv in indivs:
			indiv.geno = np.array(indiv.geno, dtype = int) # TODO do i want int8? small ints

	return indivs


def parseMulti(fileNameL, verbose = False):
	'''return list of Individuals, combined from all files in fileNameL'''

	indivs = [] # all individuals

	for fileName in fileNameL:
		if verbose:
			print("processing %s" % fileName)
		# get chr and population from file name
		temp = fileName.split('_')
		chrm = temp[1] # e.g. 'chr22', 'chrX'
		pop = temp[2]  # e.g. ASW

		# get Individual genos from this population
		popIndivs = parseFile(fileName, pop)
		indivs = indivs + popIndivs

	if verbose:
		print("\n")

	return indivs

# requires individuals to be in order when adding the j
def addFamilyInfo(indivs, famInfoFile = "relationships_w_pops_121708.txt", shuffle = True):
	'''add parent IDs to complete list of Individuals from hapmap file.
	also (optionally) shuffle. add index of final order'''
	# column order is:
	# FID	IID	dad	mom	sex	pheno	population

	dataD = {} # info from the famInfo file, keyed by indivID

	# parse fam info file
	with open(famInfoFile) as f:
		f.readline() # skip header

		for line in f:
			famID, indivID, dadID, momID, sex, pheno, pop = line.rstrip().split()
			dataD[indivID] = (famID, dadID, momID, sex)

	# add new info to exisiting indivs
	for indiv in indivs:
		famID, dadID, momID, sex = dataD[indiv.indivID]
		indiv.famID = famID
		indiv.momID = momID
		indiv.dadID = dadID
		indiv.sex = int(sex) # 0 = unknown, 1 or 2 otherwise

	if shuffle:
		random.shuffle(indivs)	

	# add indiv.j only once individuals are in final order
	j = 0
	for indiv in indivs:
		indiv.j = j
		j += 1

	return # indivs updated


def makeGenoArr(indivs):
	'''return np array of genotypes only, in order'''
	N = len(indivs)
	M = len(indivs[0].geno)

	genoArr = np.empty([N,M]) # each row is indiv genotype, each col a snp
	for j in range(N):
		genoArr[j] = indivs[j].geno

	return genoArr


def checkSNPorderPair(file1, file2):
	'''check that files contain the same snps in the same order.
	also check that each snp appears once. return true if successful.
	assumes no newlines at end of either file'''

	isMatch = True

	with open(file1) as f1:
		with open(file2) as f2:
			f1.readline() # skip header
			f2.readline()

			for line1 in f1:
				lineL1 = line1.rstrip().split(None, 3)
				lineL2 = f2.readline().rstrip().split(None, 3)

				if lineL2 == []: # empty line, if file 2 ends first
					print(file1, file2)
					print('file 2 ended first')
					isMatch = False
					break

				if lineL1[0] != lineL2[0]: # if snp rs ids don't match
					print(file1, file2)
					print('file1 has rsID: %s' % lineL1[0])
					print('file2 has rsID: %s \n' % lineL2[0])
					isMatch = False

				elif lineL1[1] != lineL2[1]: # if ref/alt don't match
					print(file1, file2)
					print('file1 has rsID with ref/alt: %s %s' % (lineL1[0], lineL1[1]))
					print('file2 has rsID with ref/alt: %s %s \n' % (lineL2[0], lineL2[1]))
					isMatch = False

				elif len(lineL1[1]) != 3: # if not exactly 1 ref, 1 alt
					print(file1, file2)
					print('not exactly one ref and alt: %s %s\n' % (lineL1[0], lineL1[1]))

			if f2.readline() != '': # if file 1 ends first
				print(file1, file2)
				print('file 1 ended first')
				isMatch = False

	return isMatch


def checkSNPorder(fileNameL):
	'''return True if all files are ok, False otherwise'''
	firstFile = fileNameL[0]
	allOK = True

	for otherFile in fileNameL[1:]:
		allOK = allOK & checkSNPorderPair(firstFile, otherFile)

	return allOK


def runParse(lsf = "ls_data.txt", checkFiles = False):
	### Process input files
	lsf = open("ls_data.txt")
	fileNameL = [line.strip() for line in lsf]
	lsf.close()

	# check input order
	if checkFiles:
		allOK = checkSNPorder(fileNameL)
		print("Result of SNP order check allOK: %s\n" % allOK)

	# read in Individuals
	indivs = parseMulti(fileNameL, verbose = True)
	addFamilyInfo(indivs)
	genoArr = makeGenoArr(indivs)

	return indivs, genoArr





