# -*- coding: utf-8 -*-
import glob
import logging
import os

from optparse import make_option
from django.core.management.base import NoArgsCommand

from utils import settingsutils
try:
    from utils.vendor.sh import install, rmdir, ErrorReturnCode
except ImportError:
    pass

LOG = logging.getLogger(__name__)


class Command(NoArgsCommand):

    option_list = NoArgsCommand.option_list + (
        make_option('--create-dirs', '-c', action='store_true', default=True, dest='create_dirs',
                    help='Create the missing directories.'),
        make_option('--delete-dirs', '-d', action='store_true', default=True, dest='delete_dirs',
                    help='Delete the superfluous directories.')
    )
    help = 'Do some operations related SAMBA.'
    smb_root = '/opt/doc'

    def handle_noargs(self, **options):
        if options.get('create_dirs'):
            self.create_dirs()

        if options.get('delete_dirs'):
            self.delete_dirs()

    def _get_count(self):
        return settingsutils.get_desktop_count()

    def create_dirs(self):
        """SAMBA users are already created, we just create the missing directories."""
        target = os.path.join(self.smb_root, 'public')
        install('-d', 'o', 'teacher', '-g', 'teacher', '-m', '755', target)
        # read current count setting
        for i in xrange(1, self._get_count() + 1):
            user = 'stu_%02d' % i
            target = os.path.join(self.smb_root, user)
            install('-d', '-o', user, '-g', user, '-m', '777', target)

    def delete_dirs(self):
        """We delete the superfluous directories, but keep SAMBA users"""
        for dirpath in glob.glob('%s/stu_*' % self.smb_root):
            idx = int(dirpath.rsplit('_', 1)[1])
            if idx > self._get_count():
                self._remove_empty_dir(dirpath)

    def _remove_empty_dir(self, dirpath):
        try:
            rmdir(dirpath)
        except ErrorReturnCode:
            LOG.exception('The directory to be deleted is not empty')
