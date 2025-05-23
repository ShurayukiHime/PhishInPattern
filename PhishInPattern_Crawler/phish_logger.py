import logging
import os
import datetime

class Phish_Logger:
	@staticmethod
	def get_phish_logger(name, file_name = 'crawl_page.py'):
		logger = logging.getLogger(name)
		logger.setLevel(logging.INFO)
		dir_path = os.path.abspath(os.path.dirname(__file__))
		handler = logging.FileHandler(os.path.join(dir_path+'/../../data/logs/',name+'_'+str(datetime.datetime.now().date())+'.log'))
		handler.setLevel(logging.INFO)

		# create a logging format
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		handler.setFormatter(formatter)

		# add the handlers to the logger
		if not logger.handlers:
			logger.addHandler(handler)
		return logger


